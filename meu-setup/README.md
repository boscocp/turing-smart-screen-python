# Meu setup do Turing Smart Screen

Esta pasta guarda **tudo que é preciso para colocar a tela Turing 3.5" para
funcionar do jeito que ela funciona hoje** — em outra máquina, ou nesta mesma
depois de formatar o Windows.

O programa que roda na tela **é este repositório**, executado por um venv local.
A instalação oficial (`turing-system-monitor.exe`) foi desinstalada.

---

## Por que este fork existe

A tela travava acesa ao desligar o PC — [issue #907][issue] do projeto original.
A causa: o programa era morto antes de conseguir enviar o comando `SCREEN_OFF`
(108) para o display. O hardware sempre apagou certo; quem não chegava a mandar
o comando era o software.

Os dois commits que corrigem isso estão nesta branch `main` e também na
[PR #1082][pr] enviada para o upstream:

| Commit    | O que faz                                                                 |
| --------- | ------------------------------------------------------------------------- |
| `bc6503e` | Espera a fila de desenho esvaziar antes de sair, para o `SCREEN_OFF` sair  |
| `774e4c8` | Desliga a tela também quando a sessão do Windows termina (logoff/shutdown) |

**Se a PR for aceita**, dá para voltar a seguir o upstream (veja
[Quando/se o PR entrar](#quandose-o-pr-entrar)).
**Se não for**, este fork continua sendo a versão que funciona — é justamente
para isso que esta pasta existe.

[issue]: https://github.com/mathoudebine/turing-smart-screen-python/issues/907
[pr]: https://github.com/mathoudebine/turing-smart-screen-python/pull/1082

---

## Instalação do zero (PC novo ou Windows formatado)

Pré-requisitos: **Python 3.9+** (aqui roda 3.13) e **git** instalados, e a tela
plugada na USB.

```powershell
git clone https://github.com/boscocp/turing-smart-screen-python.git D:\projetos-vscode\turing-smart-screen-python
cd D:\projetos-vscode\turing-smart-screen-python
powershell -ExecutionPolicy Bypass -File .\meu-setup\instalar.ps1
```

O `instalar.ps1` pede elevação sozinho e faz, nesta ordem:

1. cria o `venv` e instala o `requirements.txt`;
2. copia `meu-setup/config.yaml` → `config.yaml` e
   `meu-setup/theme-LandscapeMagicBlue.yaml` → `res/themes/LandscapeMagicBlue/theme.yaml`
   (faz `.bak-<data>` dos arquivos que já existirem);
3. marca os dois com `git update-index --skip-worktree`;
4. registra a tarefa agendada **"Turing Sistema da Tela"**;
5. cria o atalho **Turing Smart Screen** na Área de Trabalho com o ícone oficial;
6. sobe o monitor e mostra o fim do `log.log`.

O caminho não precisa ser `D:\projetos-vscode\` — o script descobre a raiz do
repositório a partir da própria localização dele.

---

## Como ele roda

### Tarefa agendada (é ela que sobe o programa)

```
Nome              : Turing Sistema da Tela
Execute           : <repo>\venv\Scripts\pythonw.exe
Arguments         : main.py
WorkingDirectory  : <repo>
RunLevel          : Highest          <-- OBRIGATÓRIO
Trigger           : AtLogon, delay PT30S
MultipleInstances : IgnoreNew
ExecutionTimeLimit: PT72H
```

**`RunLevel: Highest` não é opcional.** Com `HW_SENSORS: AUTO` o programa usa o
LibreHardwareMonitor, que exige admin; sem elevação ele aborta na hora com
`Program is not running as administrator` e nada aparece na tela.

É por isso que o atalho **não** chama o `pythonw main.py` direto.

### Atalho da Área de Trabalho (para quando a tela congela)

`Turing Smart Screen` → `wscript.exe meu-setup\reiniciar-turing.vbs`, com o
ícone `res\icons\monitor-icon-17865\icon.ico`.

O `.vbs` faz `schtasks /end` + espera 3s (a porta COM precisa ser liberada) +
`schtasks /run`. Como passa pela tarefa, herda a elevação: **sem prompt de UAC e
sem janela de console**.

Use sempre que a tela ficar parada num quadro antigo.

---

## Os arquivos pessoais

Dois arquivos do repositório são configuração pessoal e estão protegidos com
`git update-index --skip-worktree`, para não aparecerem como modificação e não
vazarem para um PR upstream:

| Arquivo                                   | Cópia mestre aqui                     |
| ----------------------------------------- | ------------------------------------- |
| `config.yaml`                             | `meu-setup/config.yaml`               |
| `res/themes/LandscapeMagicBlue/theme.yaml` | `meu-setup/theme-LandscapeMagicBlue.yaml` |

Conferir a proteção:

```powershell
git ls-files -v config.yaml res/themes/LandscapeMagicBlue/theme.yaml
# linha começando com "S" = protegido
```

**Se você mexer na config ou no tema, copie de volta para cá e commite** — é
esta pasta que sobrevive a uma formatação, não o arquivo em uso:

```powershell
Copy-Item .\config.yaml .\meu-setup\config.yaml -Force
Copy-Item .\res\themes\LandscapeMagicBlue\theme.yaml .\meu-setup\theme-LandscapeMagicBlue.yaml -Force
git add meu-setup; git commit -m "setup: atualiza config/tema"; git push boscocp main
```

### O que tem na config

Tema `LandscapeMagicBlue`, `COM_PORT: AUTO`, `HW_SENSORS: AUTO`, brilho 50,
`DISPLAY_REVERSE: true` (a tela é montada de cabeça para baixo), interface de
rede `Ethernet`, clima em pt_br. O campo `WEATHER_API_KEY` está **vazio** de
propósito — nunca commite uma chave aqui, o repositório é público.

### O que o tema tem de customizado

O `theme.yaml` é editado à mão e **não existe em nenhuma revisão do projeto
original** — se perder, não dá para recuperar do upstream. As mudanças:

- **uso da CPU** movido para o slot pequeno da esquerda (texto);
- **temperatura da CPU** promovida para o radial central (era o uso), com
  `MIN_VALUE: 20` e `INTERVAL: 5 → 2`;
- **data e hora** no topo com fonte `RobotoMono-Bold`, hora maior (18) e
  reposicionadas.

Para reverter ao original: `RADIAL.SHOW` de `CPU.PERCENTAGE` para `True` e
`RADIAL.SHOW` de `CPU.TEMPERATURE` para `False` (os blocos originais estão
comentados no arquivo).

Cópias extras fora do repositório: `D:\projetos-vscode\turing-config-backup\` e
`OneDrive\Documentos\theme.yaml`.

---

## Problemas conhecidos

**A tela ficou parada num quadro antigo.** Quase sempre o `main.py` não está
mais rodando — o último quadro simplesmente fica lá. Clique no atalho.
Confirme com:

```powershell
Get-CimInstance Win32_Process -Filter "Name='pythonw.exe'" | Select ProcessId,ParentProcessId
```

**Sempre aparecem dois `pythonw.exe`.** É o shim do venv (pai e filho). Não é
duplicação do app nem conflito na porta serial. Um só processo, ou nenhum, é que
é sinal de problema.

**O relógio do Windows pula +3h no boot.** O log do programa herda o horário
errado e, quando o horário é corrigido para trás, os registros parecem "voltar
no tempo". Não é bug do monitor, mas pode derrubá-lo — nesse caso, atalho.

**"Configure" no ícone da bandeja encerra o programa.** Ele sai para abrir a
janela de configuração; se a janela for fechada sem salvar, ninguém sobe de
volta e a tela fica congelada. Atalho resolve.

**Não há console sob `pythonw.exe`.** Todo diagnóstico sai em `log.log` na raiz
do repositório.

---

## Comandos úteis

```powershell
# estado da tarefa
Get-ScheduledTask -TaskName "Turing Sistema da Tela" | Select State
Get-ScheduledTaskInfo -TaskName "Turing Sistema da Tela"

# parar / iniciar (precisa admin)
Stop-ScheduledTask  -TaskName "Turing Sistema da Tela"
Start-ScheduledTask -TaskName "Turing Sistema da Tela"

# ver o log
Get-Content .\log.log -Tail 30

# rodar à mão para ver erros no console (PowerShell como ADMIN)
.\venv\Scripts\python.exe main.py

# atualizar o código (a vantagem do venv sobre o .exe: não precisa rebuildar)
git pull boscocp main
```

Mexer na tarefa agendada exige elevação — `Set-ScheduledTask` sem admin dá
"Acesso negado".

---

## Quando/se o PR entrar

```powershell
git pull origin main    # origin = mathoudebine (upstream)
git push boscocp main
```

O `skip-worktree` protege `config.yaml` e o tema na atualização. Se der conflito
nos arquivos de setup, o que vale é o que está em `meu-setup/`.

**Se preferir voltar ao instalador oficial:** instale o
`turing-system-monitor-3.10.0.exe`, reaponte a tarefa agendada (como admin) para
`%LOCALAPPDATA%\Programs\Turing System Monitor\main.exe` e copie
`meu-setup/config.yaml` e `meu-setup/theme-LandscapeMagicBlue.yaml` para a pasta
da instalação — o instalador traz os arquivos originais e sobrescreve os seus.

---

## Layout dos remotes

| Remote    | Aponta para                                  | Serve para                  |
| --------- | -------------------------------------------- | --------------------------- |
| `origin`  | `mathoudebine/turing-smart-screen-python`     | puxar atualizações upstream |
| `boscocp` | `boscocp/turing-smart-screen-python` (fork)   | **push vai aqui**           |

A branch `fix/flush-display-queue-before-exit` é a cabeça da PR #1082 — não
commite configuração pessoal nela. Esta `main` do fork é que carrega os fixes
**mais** o setup pessoal.
