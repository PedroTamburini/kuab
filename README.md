# Kuab

Kuab é uma interface web de chat para modelos de linguagem executados localmente com [Ollama](https://ollama.com/). O projeto também permite transcrever áudios e vídeos do YouTube com Whisper.

## Tecnologias

- Frontend: React 18 e Vite 5
- Backend: Python 3.11, FastAPI e Uvicorn
- IA local: Ollama
- Transcrição: OpenAI Whisper e FFmpeg
- Orquestração: Docker Compose

## Pré-requisitos

O modo recomendado de execução usa Docker:

- Docker Desktop ou Docker Engine
- Docker Compose v2 com suporte ao atributo `include`
- Espaço em disco suficiente para as imagens, o modelo do Whisper e os modelos do Ollama

Para aceleração por GPU, o host também precisa estar configurado para disponibilizar a GPU aos contêineres:

- NVIDIA: drivers NVIDIA e NVIDIA Container Toolkit
- AMD: ambiente Linux com ROCm e acesso a `/dev/kfd` e `/dev/dri`

Se não houver uma GPU compatível, use a configuração para CPU.

## Executando com Docker Compose

Execute os comandos a partir da raiz do repositório. Escolha somente um dos arquivos abaixo de acordo com o hardware:

| Hardware | Arquivo Compose |
| --- | --- |
| Somente CPU | `compose-cpu.yml` |
| GPU NVIDIA | `compose-nvidia.yml` |
| GPU AMD/ROCm | `compose-amd.yml` |

Nos exemplos seguintes, substitua `compose-cpu.yml` pelo arquivo correspondente ao seu hardware quando necessário.

### 1. Construir e iniciar os serviços

```bash
docker compose -f compose-cpu.yml up --build -d
```

O primeiro início pode demorar: além da construção das imagens, o backend baixa e carrega o modelo `base` do Whisper.

### 2. Baixar um modelo no Ollama

Escolha um modelo compatível com os recursos da sua máquina e substitua `NOME_DO_MODELO` no comando:

```bash
docker compose -f compose-cpu.yml exec ollama ollama pull NOME_DO_MODELO
```

Confira os modelos instalados:

```bash
docker compose -f compose-cpu.yml exec ollama ollama list
```

O Kuab não define um modelo fixo. Os modelos disponíveis no seletor da interface são obtidos diretamente do Ollama.

### 3. Acessar a aplicação

- Interface web: <http://localhost:5173>
- API: <http://localhost:8000>
- Documentação interativa da API: <http://localhost:8000/docs>
- Verificação de saúde do backend: <http://localhost:8000/health>
- API do Ollama: <http://localhost:11434>

### Logs e encerramento

Acompanhe os logs de todos os serviços:

```bash
docker compose -f compose-cpu.yml logs -f
```

Ou acompanhe apenas o backend:

```bash
docker compose -f compose-cpu.yml logs -f backend
```

Encerre e remova os contêineres e a rede do projeto:

```bash
docker compose -f compose-cpu.yml down
```

Os modelos do Ollama ficam preservados em um volume Docker. Para também apagar esse volume e todos os modelos baixados por essa configuração, use `docker compose -f compose-cpu.yml down -v`.

## Executando localmente para desenvolvimento

Neste modo, Ollama, backend e frontend são iniciados separadamente.

### 1. Ollama

Instale o Ollama e inicie o servidor:

```bash
ollama serve
```

Com o servidor ativo, abra outro terminal e baixe um modelo de sua escolha:

```bash
ollama pull NOME_DO_MODELO
```

Por padrão, o backend procura o Ollama em `http://localhost:11434`.

### 2. Backend

Requisitos locais:

- Python 3.11
- FFmpeg disponível no `PATH`

Crie um ambiente virtual e instale as dependências:

```bash
cd backend
python -m venv .venv
```

Ative o ambiente no Linux ou macOS:

```bash
source .venv/bin/activate
```

Ou no PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Instale e inicie a API:

```bash
python -m pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Para usar um Ollama em outro endereço, defina `OLLAMA_URL` antes de iniciar o backend:

```bash
export OLLAMA_URL=http://servidor-ollama:11434
```

No PowerShell, use:

```powershell
$env:OLLAMA_URL = "http://servidor-ollama:11434"
```

### 3. Frontend

Em outro terminal, com Node.js 20 ou superior:

```bash
cd frontend
npm install
npm run dev
```

Acesse <http://localhost:5173>. Atualmente, o frontend espera que o backend esteja disponível em `http://localhost:8000`.

## Estrutura do projeto

```text
.
├── backend/              # API, integração com Ollama e transcrição
├── frontend/             # Interface React/Vite
├── common.yml            # Serviços compartilhados do Compose
├── compose-cpu.yml       # Ollama para CPU
├── compose-nvidia.yml    # Ollama com GPU NVIDIA
└── compose-amd.yml       # Ollama com ROCm para GPU AMD
```

O diretório `backend/dataset_marubo` contém o conjunto de dados e os scripts de preparação e validação. Consulte [`backend/dataset_marubo/README.md`](backend/dataset_marubo/README.md) para detalhes específicos do dataset.

## Solução de problemas

### O seletor de modelos está vazio

Verifique se há ao menos um modelo instalado:

```bash
docker compose -f compose-cpu.yml exec ollama ollama list
```

Se a lista estiver vazia, execute `ollama pull` conforme descrito acima e recarregue a página.

### O backend não consegue acessar o Ollama

Confirme se os serviços estão ativos e examine os logs:

```bash
docker compose -f compose-cpu.yml ps
docker compose -f compose-cpu.yml logs ollama backend
```

No Docker, o backend usa `OLLAMA_URL=http://ollama:11434`. Na execução local, o valor padrão é `http://localhost:11434`.

### A transcrição falha ou o backend demora para ficar pronto

O Whisper carrega o modelo `base` durante a inicialização do backend. No primeiro uso, aguarde o download terminar e acompanhe `docker compose -f compose-cpu.yml logs -f backend`. A transcrição de vídeos do YouTube também depende de acesso à internet e pode ser afetada por mudanças ou restrições da plataforma.

### Uma porta já está em uso

Os serviços usam as portas `5173`, `8000` e `11434`. Encerre o processo que ocupa a porta ou ajuste o mapeamento correspondente nos arquivos Compose e, no caso do backend, também a URL usada pelo frontend.

## Licença

Consulte o arquivo [LICENSE](LICENSE).
