$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$root=Split-Path -Parent $PSScriptRoot
$a=[Reflection.Assembly]::LoadFile((Join-Path $root 'releases\current\Antigravity-Recovery-Launcher.exe'))
$flags=[Reflection.BindingFlags]'NonPublic,Public,Instance,Static'
$p=$a.GetType('AntigravityLauncher.Program')
$prior=$p.GetMethod('EnterSharpCardDpiContext',$flags).Invoke($null,@())
$t=$a.GetType('AntigravityLauncher.AntigravityHotLaunchChoiceForm')
$form=[Activator]::CreateInstance($t,$true)
try {
 $t.GetMethod('StopTimer',$flags).Invoke($form,@()) | Out-Null
 $scale=[float]$t.GetField('uiScale',$flags).GetValue($form)
 $actual=($form.ClientSize.Width/560.0)
 if([Math]::Abs($actual-$scale) -gt 0.02){throw 'window_and_paint_scale_disagree'}
 Write-Output ('Actual desktop DPI scale: '+$scale+'; card='+$form.ClientSize.Width+'x'+$form.ClientSize.Height)
} finally { $form.Dispose() }
foreach($scale in @(1.0,1.5,2.0)) {
 $form=[Activator]::CreateInstance($t,$true)
 try {
  $t.GetMethod('StopTimer',$flags).Invoke($form,@()) | Out-Null
  $existing=[float]$t.GetField('uiScale',$flags).GetValue($form)
  $form.Scale((New-Object Drawing.SizeF(($scale/$existing),($scale/$existing))))
  $t.GetField('uiScale',$flags).SetValue($form,[float]$scale)
  $rect=$t.GetMethod('Px',$flags)
  $icon=$rect.Invoke($form,@(20,18,34,34))
  $note=$rect.Invoke($form,@(20,64,520,22))
  $account=$rect.Invoke($form,@(20,94,520,24))
  $selection=$rect.Invoke($form,@(20,124,520,22))
  $network=$rect.Invoke($form,@(20,154,520,24))
  if($icon.Bottom -ge $note.Top -or $note.Bottom -ge $account.Top -or $account.Bottom -ge $selection.Top -or $selection.Bottom -ge $network.Top){throw 'content_overlap'}
  foreach($name in @('btnActivate','btnRepair')) {
   $button=$t.GetField($name,$flags).GetValue($form)
   if($network.Bottom -ge $button.Top -or $button.Bottom -gt $form.ClientSize.Height){throw 'button_overlap_or_clipping'}
  }
  $bitmap=New-Object Drawing.Bitmap($form.Width,$form.Height)
  try {$form.DrawToBitmap($bitmap,$form.ClientRectangle)} finally {$bitmap.Dispose()}
  Write-Output ('PASS: '+($scale*100)+'% layout has separated icon/text/buttons and renders without exceptions')
 } finally {$form.Dispose()}
}
if($prior -ne [IntPtr]::Zero){$null=$p.GetMethod('SetThreadDpiAwarenessContext',$flags).Invoke($null,@($prior))}
