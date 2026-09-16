' Reinicia o monitor da tela Turing (turing-smart-screen-python).
'
' O main.py precisa rodar como administrador (LibreHardwareMonitor), entao este
' script NAO chama o python direto: ele para e religa a tarefa agendada, que ja
' roda com privilegio elevado - assim nao aparece prompt de UAC.
'
' Uso tipico: a tela congelou (ajuste de relogio, cabo, etc) -> clica no atalho.
' O atalho da Area de Trabalho e criado por instalar.ps1.

Const TAREFA = "Turing Sistema da Tela"

Dim sh
Set sh = CreateObject("WScript.Shell")

' 1) derruba a instancia atual (travada ou nao) e espera a porta COM liberar
sh.Run "schtasks /end /tn """ & TAREFA & """", 0, True
WScript.Sleep 3000

' 2) sobe de novo
sh.Run "schtasks /run /tn """ & TAREFA & """", 0, True
