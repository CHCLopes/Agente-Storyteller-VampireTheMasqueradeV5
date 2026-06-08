$WshShell = New-Object -ComObject WScript.Shell
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Get-Item $ScriptDir).Parent.FullName

$ShortcutPath = Join-Path $ProjectRoot "Iniciar o Jogo.lnk"
$TargetPath = Join-Path $ProjectRoot "INICIAR_JOGO.bat"
$IconPath = Join-Path $ProjectRoot "vampire-icon.ico"

$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $TargetPath
$Shortcut.WorkingDirectory = $ProjectRoot
$Shortcut.IconLocation = $IconPath
$Shortcut.WindowStyle = 1
$Shortcut.Description = "Iniciar Agente Storyteller V5"
$Shortcut.Save()

Write-Output "[✓] Atalho Windows atualizado com sucesso."
