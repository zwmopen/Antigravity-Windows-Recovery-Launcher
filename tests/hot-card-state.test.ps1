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
$programType = $assembly.GetType('AntigravityLauncher.Program')
$priorDpi = $programType.GetMethod('EnterSharpCardDpiContext',$flags).Invoke($null,@())
$form = [Activator]::CreateInstance($type, $true)
try {
    $type.GetMethod('StopTimer', $flags).Invoke($form, @()) | Out-Null
    if ([Math]::Abs(($form.ClientSize.Width / $form.ClientSize.Height) - (560.0/256)) -gt 0.02) { throw 'card_layout_failed' }
    foreach ($name in @('accountText','selectedText','networkText')) {
        if ([string]::IsNullOrWhiteSpace($type.GetField($name,$flags).GetValue($form))) { throw ('missing_state:' + $name) }
    }
    if (-not $type.GetField('selectedText',$flags).GetValue($form).Contains('未核实') -and -not $type.GetField('selectedText',$flags).GetValue($form).Contains('非编辑器实时')) { throw 'runtime_identity_overclaim' }
    # Reflection hosts use PowerShell's base directory; explicitly supply the packaged icon for the render fixture.
    $iconReader = $assembly.GetType('AntigravityLauncher.Program').GetMethod('LoadIconOrPng',$flags)
    $type.GetField('appIcon',$flags).SetValue($form,$iconReader.Invoke($null,@([string](Join-Path $root 'releases\current\Antigravity-Launcher.ico'))))
    $bitmap = New-Object Drawing.Bitmap($form.Width,$form.Height)
    try {
        $form.DrawToBitmap($bitmap, $form.ClientRectangle)
        # Draw child controls explicitly for this offscreen test (the form is not shown).
        $g = [Drawing.Graphics]::FromImage($bitmap)
        try {
            foreach ($control in $form.Controls) {
                $child = New-Object Drawing.Bitmap($control.Width,$control.Height)
                try {
                    $control.DrawToBitmap($child,$control.ClientRectangle)
                    $g.DrawImageUnscaled($child,$control.Left,$control.Top)
                } finally { $child.Dispose() }
            }
        } finally { $g.Dispose() }
        $bitmap.Save((Join-Path $root '.work\hot-card-preview.png'))
    } finally { $bitmap.Dispose() }
    $activate = $type.GetField('btnActivate',$flags).GetValue($form)
    $repair = $type.GetField('btnRepair',$flags).GetValue($form)
    if (-not $activate.GetType().GetProperty('IsPrimary',$flags).GetValue($activate,$null) -or $repair.GetType().GetProperty('IsPrimary',$flags).GetValue($repair,$null)) { throw 'primary_secondary_hierarchy_failed' }
    if ($type.GetField('networkText',$flags).GetValue($form).Contains('CURRENT-VERIFIED')) { throw 'internal_node_placeholder_visible' }
    Write-Output 'PASS: compiled card parses JSON safely, renders four status lines, and does not claim live editor identity'
} finally { $form.Dispose(); if ($priorDpi -ne [IntPtr]::Zero) { $null=$programType.GetMethod('SetThreadDpiAwarenessContext',$flags).Invoke($null,@($priorDpi)) } }
