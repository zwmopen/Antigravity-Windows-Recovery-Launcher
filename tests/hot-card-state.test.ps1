$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$root = Split-Path -Parent $PSScriptRoot
$assembly = [Reflection.Assembly]::LoadFile((Join-Path $root 'releases\current\Antigravity-Recovery-Launcher.exe'))
$type = $assembly.GetType('AntigravityLauncher.AntigravityHotLaunchChoiceForm')
$flags = [Reflection.BindingFlags]'NonPublic,Public,Instance,Static'
$reader = $type.GetMethod('JsonValue', $flags)
if ($reader.Invoke($null, @('{"email":"a@example.com","node":"JP 日本"}', 'email')) -ne 'a@example.com') { throw 'json_read_failed' }
if ($reader.Invoke($null, @('{bad', 'email')) -ne '') { throw 'malformed_state_not_safe' }
$form = [Activator]::CreateInstance($type, $true)
try {
    $type.GetMethod('StopTimer', $flags).Invoke($form, @()) | Out-Null
    if ($form.ClientSize.Width -ne 560 -or $form.ClientSize.Height -ne 224) { throw 'card_layout_failed' }
    foreach ($name in @('accountText','selectedText','networkText')) {
        if ([string]::IsNullOrWhiteSpace($type.GetField($name,$flags).GetValue($form))) { throw ('missing_state:' + $name) }
    }
    if (-not $type.GetField('accountText',$flags).GetValue($form).Contains('未核实') -and -not $type.GetField('accountText',$flags).GetValue($form).Contains('非编辑器实时')) { throw 'runtime_identity_overclaim' }
    $bitmap = New-Object Drawing.Bitmap($form.Width,$form.Height)
    try { $form.DrawToBitmap($bitmap, $form.ClientRectangle) } finally { $bitmap.Dispose() }
    Write-Output 'PASS: compiled card parses JSON safely, renders four status lines, and does not claim live editor identity'
} finally { $form.Dispose() }
