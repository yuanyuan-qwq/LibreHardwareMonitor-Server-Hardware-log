#Requires -RunAsAdministrator
# Registers separate hourly collection, daily reporting, and retention tasks.

[CmdletBinding()]
param(
    [string]$CollectTaskName = 'LibreHardwareMonitor - Collect Hourly',
    [string]$ReportTaskName = 'LibreHardwareMonitor - Send Daily Report',
    [string]$CleanupTaskName = 'LibreHardwareMonitor - Cleanup Daily Logs'
)

$ErrorActionPreference = 'Stop'
$projectDirectory = $PSScriptRoot
$python = (& py -c 'import sys; print(sys.executable)').Trim()
if (-not (Test-Path -LiteralPath $python)) {
    throw 'Python executable not found. Install Python for the current Windows account first.'
}

$scriptPath = Join-Path $projectDirectory 'run_monitor.py'
$account = "$env:USERDOMAIN\$env:USERNAME"
$credential = Get-Credential -UserName $account -Message 'Enter the Windows account password used by the scheduled tasks.'
$password = $credential.GetNetworkCredential().Password

function Register-MonitorTask {
    param(
        [Parameter(Mandatory)] [string]$Name,
        [Parameter(Mandatory)] [string]$Mode,
        [Parameter(Mandatory)] $Trigger,
        [Parameter(Mandatory)] [string]$Description
    )

    $action = New-ScheduledTaskAction `
        -Execute $python `
        -Argument ('"{0}" {1}' -f $scriptPath, $Mode) `
        -WorkingDirectory $projectDirectory
    $settings = New-ScheduledTaskSettingsSet `
        -StartWhenAvailable `
        -MultipleInstances IgnoreNew `
        -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

    Register-ScheduledTask `
        -TaskName $Name `
        -Description $Description `
        -Action $action `
        -Trigger $Trigger `
        -Settings $settings `
        -User $credential.UserName `
        -Password $password `
        -RunLevel Highest `
        -Force | Out-Null
}

$nextFullHour = (Get-Date).Date.AddHours((Get-Date).Hour + 1)
$collectTrigger = New-ScheduledTaskTrigger `
    -Once `
    -At $nextFullHour `
    -RepetitionInterval (New-TimeSpan -Hours 1)
$reportTrigger = New-ScheduledTaskTrigger -Daily -At '11:59 PM'
$cleanupTrigger = New-ScheduledTaskTrigger -Daily -At '12:15 AM'

Register-MonitorTask `
    -Name $CollectTaskName `
    -Mode 'collect' `
    -Trigger $collectTrigger `
    -Description 'Collect LibreHardwareMonitor and Windows metrics every hour and append the current daily CSV.'
Register-MonitorTask `
    -Name $ReportTaskName `
    -Mode 'report' `
    -Trigger $reportTrigger `
    -Description 'Send one LibreHardwareMonitor daily email report at 11:59 PM.'
Register-MonitorTask `
    -Name $CleanupTaskName `
    -Mode 'cleanup' `
    -Trigger $cleanupTrigger `
    -Description 'Delete LibreHardwareMonitor daily CSV files outside the seven-day retention window.'

@(
    'HWiNFO64 - Send Hourly Report',
    'LibreHardwareMonitor - Send Hourly Report'
) | ForEach-Object {
    if (Get-ScheduledTask -TaskName $_ -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $_ -Confirm:$false
    }
}

Write-Host 'Created scheduled tasks:' -ForegroundColor Green
Write-Host "  $CollectTaskName  (hourly at the top of the hour)"
Write-Host "  $ReportTaskName  (daily at 11:59 PM)"
Write-Host "  $CleanupTaskName  (daily at 12:15 AM)"
Write-Host "Python : $python"
Write-Host "Script : $scriptPath"
