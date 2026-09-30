[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("start", "stop", "restart", "status")]
    [string]$Action = "start"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Port = 8000
$ManagedPidPath = Join-Path $env:TEMP "clue-ai-server.pid"

function Get-ListenerProcessIds {
    $portSuffix = ":{0}$" -f $Port
    $ids = @()
    foreach ($line in (netstat.exe -ano -p tcp 2>$null)) {
        $fields = @($line.Trim() -split "\s+" | Where-Object { $_ })
        if ($fields.Count -lt 5) {
            continue
        }

        if ($fields[1] -match $portSuffix -and $fields[-2] -eq "LISTENING" -and $fields[-1] -match "^\d+$") {
            $ids += [int]$fields[-1]
        }
    }
    return @($ids | Sort-Object -Unique)
}

function Get-CondaCommand {
    $conda = Get-Command conda -ErrorAction Stop
    return $conda.Source
}

function Get-GenPythonPath {
    $conda = Get-CondaCommand
    $output = & $conda run -n gen python -c "import sys; print(sys.executable)"
    if ($LASTEXITCODE -ne 0 -or $output.Count -eq 0) {
        throw "Could not find Python in the Conda 'gen' environment."
    }
    $pythonPath = @($output | ForEach-Object { ([string]$_).Trim() } | Where-Object { $_ } | Select-Object -Last 1)
    if ($pythonPath.Count -eq 0) {
        throw "Could not find Python in the Conda 'gen' environment."
    }
    return [System.IO.Path]::GetFullPath([string]$pythonPath[0])
}

function Remove-ManagedPidIfMatches([int]$ProcessId) {
    if (-not (Test-Path -LiteralPath $ManagedPidPath)) {
        return
    }

    $recordedPid = [string](Get-Content -LiteralPath $ManagedPidPath -Raw -ErrorAction SilentlyContinue)
    $recordedPid = $recordedPid.Trim()
    if ($recordedPid -eq [string]$ProcessId) {
        Remove-Item -LiteralPath $ManagedPidPath -Force
    }
}

function Stop-ClueServer {
    $listenerIds = @(Get-ListenerProcessIds)
    $managedPid = $null
    if (Test-Path -LiteralPath $ManagedPidPath) {
        $recordedPid = [string](Get-Content -LiteralPath $ManagedPidPath -Raw -ErrorAction SilentlyContinue)
        $recordedPid = $recordedPid.Trim()
        if ($recordedPid -match "^\d+$") {
            $managedPid = [int]$recordedPid
            if ($listenerIds.Count -eq 0 -and (Get-Process -Id $managedPid -ErrorAction SilentlyContinue)) {
                $listenerIds += $managedPid
            }
        }
    }

    if ($listenerIds.Count -eq 0) {
        if (Test-Path -LiteralPath $ManagedPidPath) {
            Remove-Item -LiteralPath $ManagedPidPath -Force
        }
        Write-Host "Port $Port is already free."
        return
    }

    $genPythonPath = Get-GenPythonPath
    foreach ($listenerId in $listenerIds) {
        $process = Get-Process -Id $listenerId -ErrorAction SilentlyContinue
        if ($null -eq $process) {
            continue
        }

        $processPath = $process.Path
        if ($process.ProcessName -notin @("python", "pythonw") -or -not $processPath) {
            throw "Port $Port is owned by PID $listenerId ($($process.ProcessName)). Refusing to stop a non-Python process."
        }

        $processPath = [System.IO.Path]::GetFullPath($processPath)
        if (-not [string]::Equals($processPath, $genPythonPath, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Port $Port is owned by PID $listenerId from '$processPath'. Refusing to stop a process outside the Conda 'gen' environment."
        }

        Write-Host "Stopping the Python server on port $Port (PID $listenerId)."
        $wasManaged = $managedPid -eq $listenerId
        if ($wasManaged) {
            Remove-ManagedPidIfMatches $listenerId
        }
        try {
            Stop-Process -Id $listenerId -Force
        }
        catch {
            if ($wasManaged) {
                Set-Content -LiteralPath $ManagedPidPath -Value $listenerId -NoNewline
            }
            throw
        }
    }

    $deadline = [DateTime]::UtcNow.AddSeconds(5)
    $processStillRunning = $false
    do {
        $processStillRunning = $false
        if ($managedPid) {
            $processStillRunning = [bool](Get-Process -Id $managedPid -ErrorAction SilentlyContinue)
        }
        if ((@(Get-ListenerProcessIds).Count -eq 0) -and -not $processStillRunning) {
            break
        }
        Start-Sleep -Milliseconds 100
    } while ([DateTime]::UtcNow -lt $deadline)

    $remaining = @(Get-ListenerProcessIds)
    if ($remaining.Count -gt 0) {
        throw "Port $Port is still in use by PID(s): $($remaining -join ', ')."
    }
    Write-Host "Port $Port is free. Local profile and .data files were not changed."
}

function Start-ClueServer {
    $listenerIds = @(Get-ListenerProcessIds)
    if ($listenerIds.Count -gt 0) {
        throw "Port $Port is already in use by PID(s): $($listenerIds -join ', '). Run '.\scripts\clue.ps1 restart' to close the Conda 'gen' server and start Clue."
    }

    if (Test-Path -LiteralPath $ManagedPidPath) {
        $recordedPid = [string](Get-Content -LiteralPath $ManagedPidPath -Raw -ErrorAction SilentlyContinue)
        $recordedPid = $recordedPid.Trim()
        if ($recordedPid -match "^\d+$" -and (Get-Process -Id ([int]$recordedPid) -ErrorAction SilentlyContinue)) {
            throw "A Clue startup is already running as PID $recordedPid. Run '.\scripts\clue.ps1 stop' first."
        }
        Remove-Item -LiteralPath $ManagedPidPath -Force
    }

    $genPythonPath = Get-GenPythonPath
    Push-Location $ProjectRoot
    try {
        Write-Host "Starting Clue on http://127.0.0.1:$Port. Press Ctrl+C here to stop it."
        $process = Start-Process -FilePath $genPythonPath -ArgumentList @("-m", "clue_ai") -WorkingDirectory $ProjectRoot -NoNewWindow -PassThru
        Set-Content -LiteralPath $ManagedPidPath -Value $process.Id -NoNewline
        $process.WaitForExit()
        $exitCode = $process.ExitCode
        $stillMarkedManaged = Test-Path -LiteralPath $ManagedPidPath
        if ($stillMarkedManaged -and $exitCode -ne 0) {
            throw "Clue exited with code $exitCode."
        }
        if (-not $stillMarkedManaged) {
            Write-Host "Clue stopped."
        }
        elseif ($exitCode -eq 0) {
            Write-Host "Clue stopped."
        }
    }
    finally {
        if ($process) {
            Remove-ManagedPidIfMatches $process.Id
        }
        Pop-Location
    }
}

switch ($Action) {
    "start" {
        Start-ClueServer
    }
    "stop" {
        Stop-ClueServer
    }
    "restart" {
        Stop-ClueServer
        Start-ClueServer
    }
    "status" {
        $listenerIds = @(Get-ListenerProcessIds)
        if ($listenerIds.Count -eq 0) {
            Write-Host "Clue is stopped; port $Port is free."
        }
        else {
            foreach ($listenerId in $listenerIds) {
                $process = Get-Process -Id $listenerId -ErrorAction SilentlyContinue
                $name = if ($process) { $process.ProcessName } else { "unknown process" }
                Write-Host "Port $Port is listening (PID $listenerId, $name)."
            }
        }
    }
}
