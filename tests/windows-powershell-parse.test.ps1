param([string]$Path = (Join-Path $PSScriptRoot '..\src\Antigravity-ProxySupervisor.ps1'))
$tokens=$null
$errors=$null
[System.Management.Automation.Language.Parser]::ParseFile($Path,[ref]$tokens,[ref]$errors) | Out-Null
foreach($parseIssue in $errors) { Write-Output ('line={0} {1}' -f $parseIssue.Extent.StartLineNumber,$parseIssue.Message) }
if($errors.Count -gt 0){exit 1}
Write-Output ('parse_pass PowerShell=' + $PSVersionTable.PSVersion)
