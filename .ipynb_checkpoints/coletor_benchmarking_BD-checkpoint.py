import json
import time
import csv
import platform
import socket
import getpass
from pathlib import Path
from datetime import datetime


class ColetorBenchmarkingBD:
    """
    Coletor de baseline para estudos de Avaliação de Desempenho (AVD).

    Objetivos:
    - Registrar dados brutos individuais
    - Permitir replicabilidade
    - Produzir metadados do experimento
    - Separar warmup de coleta oficial
    - Registrar cache frio/quente
    - Registrar erros sem contaminar estatística
    """

    def __init__(
        self,
        sistema_id,
        arquivo_queries="queries.json",
        nome_arquivo="benchmarking_amazon_2006.csv",
        dataset="amazon_2006",
        warmup=5
    ):
        """
        :param sistema_id:
            Nome do sistema avaliado.
            Ex: postgres, mongodb, neo4j

        :param arquivo_queries:
            Arquivo JSON contendo queries.

        :param nome_arquivo:
            Nome do CSV de saída.

        :param dataset:
            Nome da carga/dataset.

        :param warmup:
            Número de execuções de aquecimento.
        """

        self.sistema_id = sistema_id
        self.dataset = dataset
        self.warmup = warmup

        diretorio_script = Path(__file__).parent.absolute()

        self.caminho_queries = diretorio_script / arquivo_queries

        self.pasta_saida = diretorio_script / "out"
        self.pasta_saida.mkdir(parents=True, exist_ok=True)

        self.caminho_saida = self.pasta_saida / nome_arquivo

        self.caminho_metadados = (
            self.pasta_saida /
            f"metadata_{self.sistema_id}.json"
        )

        self.caminho_planos = (
            self.pasta_saida /
            f"planos_{self.sistema_id}.txt"
        )

        self.queries_json = self._carregar_queries()

    # =========================================================
    # CARREGAMENTO DE QUERIES
    # =========================================================

    def _carregar_queries(self):
        """Carrega queries do JSON."""

        if not self.caminho_queries.exists():
            print(f"[ERRO] Arquivo não encontrado:")
            print(self.caminho_queries)
            return []

        try:
            with open(self.caminho_queries, "r", encoding="utf-8") as f:
                dados = json.load(f)

            print(f"[OK] {len(dados)} queries carregadas.")
            return dados

        except Exception as e:
            print(f"[ERRO] Falha ao carregar queries:")
            print(str(e))
            return []

    # =========================================================
    # METADADOS
    # =========================================================

    def salvar_metadados(
        self,
        db_versao="desconhecida",
        observacoes=""
    ):
        """
        Salva metadados do experimento.
        """

        metadados = {
            "timestamp_inicio": datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

            "sistema_avaliado": self.sistema_id,
            "versao_banco": db_versao,

            "dataset": self.dataset,

            "total_queries": len(self.queries_json),

            "warmup_execucoes": self.warmup,

            "sistema_operacional": platform.platform(),

            "hostname": socket.gethostname(),

            "usuario_execucao": getpass.getuser(),

            "python_versao": platform.python_version(),

            "processador": platform.processor(),

            "arquitetura": platform.machine(),

            "observacoes": observacoes
        }

        with open(
            self.caminho_metadados,
            "w",
            encoding="utf-8"
        ) as f:
            json.dump(
                metadados,
                f,
                indent=4,
                ensure_ascii=False
            )

        print("[OK] Metadados salvos.")

    # =========================================================
    # CSV
    # =========================================================

    def _criar_csv_se_necessario(self):
        """Cria/Reseta o CSV com cabeçalho apenas na primeira execução do objeto."""
        
        if getattr(self, '_csv_inicializado', False):
            return

        with open(
            self.caminho_saida,
            "w",
            newline="",
            encoding="utf-8"
        ) as f:
            escritor = csv.writer(f, delimiter=';')
            escritor.writerow([
                "run", "timestamp", "sistema", "query_id", "carga", 
                "categoria", "metrica", "unidade", "valor", "tempo", 
                "num_tuplas", "observacao"
            ])
        
        self._csv_inicializado = True

    def registrar(
        self,
        run,
        query_id,
        titulo,
        categoria,
        tempo_ms,
        num_tuplas,
        obs
    ):
        """
        Registra UMA execução individual.
        """

        tp_ms = num_tuplas / tempo_ms if tempo_ms > 0 else 0

        self._criar_csv_se_necessario()

        with open(
            self.caminho_saida,
            "a",
            newline="",
            encoding="utf-8"
        ) as f:

            escritor = csv.writer(f, delimiter=';')

            escritor.writerow([
                run,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                self.sistema_id,
                query_id,
                titulo,
                categoria,
                "tuplas por milissegundos",
                "tp/ms",
                tp_ms,
                f"{tempo_ms:.4f}",
                num_tuplas,
                obs,
            ])

    # =========================================================
    # WARMUPa
    # =========================================================

    def salvar_planos_execucao(self, cursor):
        """
        Salva em TXT:
        - plano de execução
        - índices utilizados
        - buffers/cache

        Apenas uma vez por consulta.
        """

        print("\n[PLANOS] Coletando planos de execução...")

        with open(
            self.caminho_planos,
            "w",
            encoding="utf-8"
        ) as arquivo:

            arquivo.write("=" * 100 + "\n")
            arquivo.write("PLANOS DE EXECUÇÃO DAS CONSULTAS\n")
            arquivo.write("=" * 100 + "\n\n")

            for item in self.queries_json:

                query_id = item.get("id")
                titulo = item.get("titulo", "sem_titulo")
                categoria = item.get("categoria", "desconhecida")
                sql = item.get("sql")

                if not sql:
                    continue

                try:

                    explain_sql = f"""
                    EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
                    {sql}
                    """

                    cursor.execute(explain_sql)

                    plano = cursor.fetchall()

                    plano_texto = "\n".join(
                        linha[0]
                        for linha in plano
                    )

                    # -----------------------------------------
                    # Detectar índices
                    # -----------------------------------------

                    indices_detectados = []

                    for linha in plano_texto.splitlines():

                        if "Index Scan" in linha:
                            indices_detectados.append(
                                linha.strip()
                            )

                        elif "Bitmap Index Scan" in linha:
                            indices_detectados.append(
                                linha.strip()
                            )

                    if not indices_detectados:
                        indices_detectados.append(
                            "Nenhum índice detectado."
                        )

                    # -----------------------------------------
                    # Detectar buffers/cache
                    # -----------------------------------------

                    buffers = []

                    for linha in plano_texto.splitlines():

                        if "Buffers:" in linha:
                            buffers.append(
                                linha.strip()
                            )

                    if not buffers:
                        buffers.append(
                            "Informações de buffer não encontradas."
                        )

                    # -----------------------------------------
                    # Escrever no TXT
                    # -----------------------------------------

                    arquivo.write("=" * 100 + "\n")
                    arquivo.write(f"QUERY ID : {query_id}\n")
                    arquivo.write(f"TÍTULO   : {titulo}\n")
                    arquivo.write(f"CATEGORIA: {categoria}\n")
                    arquivo.write("=" * 100 + "\n\n")

                    arquivo.write("SQL:\n")
                    arquivo.write("-" * 100 + "\n")
                    arquivo.write(sql.strip())
                    arquivo.write("\n\n")

                    arquivo.write("PLANO DE EXECUÇÃO:\n")
                    arquivo.write("-" * 100 + "\n")
                    arquivo.write(plano_texto)
                    arquivo.write("\n\n")

                    arquivo.write("ÍNDICES DETECTADOS:\n")
                    arquivo.write("-" * 100 + "\n")

                    for idx in indices_detectados:
                        arquivo.write(idx + "\n")

                    arquivo.write("\n")

                    arquivo.write("CACHE / BUFFERS:\n")
                    arquivo.write("-" * 100 + "\n")

                    for b in buffers:
                        arquivo.write(b + "\n")

                    arquivo.write("\n\n")

                    print(
                        f"[OK] Plano da Query {query_id} salvo."
                    )

                except Exception as e:

                    arquivo.write("=" * 100 + "\n")
                    arquivo.write(
                        f"ERRO NA QUERY {query_id}\n"
                    )
                    arquivo.write("=" * 100 + "\n")
                    arquivo.write(str(e))
                    arquivo.write("\n\n")

                    print(
                        f"[ERRO] Query {query_id}: {e}"
                    )

        print("[OK] Planos salvos.")

    def executar_warmup(self, cursor):
        """
        Executa warmup sem registrar resultados.
        """

        if self.warmup <= 0:
            return

        print(f"\n[WARMUP] Executando {self.warmup} warmups...")

        # -----------------------------------------------------
        # Salvar planos UMA vez
        # -----------------------------------------------------

        self.salvar_planos_execucao(cursor)

        for item in self.queries_json:

            sql = item.get("sql")

            if not sql:
                continue

            for _ in range(self.warmup):

                try:
                    cursor.execute(sql)

                    if cursor.description:
                        cursor.fetchall()

                except Exception:
                    pass

        print("[OK] Warmup finalizado.")

    # =========================================================
    # EXECUÇÃO PRINCIPAL
    # =========================================================

    def executar_experimento(
        self,
        cursor,
        repeticoes=40
    ):
        """
        Executa benchmark completo.
        """

        if not self.queries_json:
            print("[ERRO] Nenhuma query carregada.")
            return

        print("\n================================================")
        print("INICIANDO COLETA DE BASELINE")
        print("================================================")

        print(f"Sistema : {self.sistema_id}")
        print(f"Dataset : {self.dataset}")
        print(f"Queries : {len(self.queries_json)}")
        print(f"Runs    : {repeticoes}")

        # -----------------------------------------------------
        # Warmup
        # -----------------------------------------------------

        self.executar_warmup(cursor)

        # -----------------------------------------------------
        # Coleta oficial
        # -----------------------------------------------------

        for r in range(1, repeticoes + 1):

            print(f"\n[RUN {r}/{repeticoes}]")

            for item in self.queries_json:

                query_id = item.get("id")
                titulo = item.get("titulo", "sem_titulo")
                categoria = item.get("categoria", "desconhecida")
                sql = item.get("sql")

                if not sql:
                    continue

                cache = "cache quente"

                try:

                    inicio = time.perf_counter()

                    cursor.execute(sql)

                    resultados = (
                        cursor.fetchall()
                        if cursor.description
                        else []
                    )

                    fim = time.perf_counter()

                    tempo_ms = (fim - inicio) * 1000

                    num_tuplas = len(resultados)

                    self.registrar(
                        run=r,
                        query_id=query_id,
                        titulo=titulo,
                        categoria=categoria,
                        tempo_ms=tempo_ms,
                        num_tuplas=num_tuplas,
                        obs=cache
                    )

                    print(
                        f"  Q{query_id:<2} | "
                        f"{tempo_ms:>9.3f} ms | "
                        f"{num_tuplas:>6} tuplas"
                    )

                except Exception as e:

                    erro = str(e).replace("\n", " ")

                    print(
                        f"  Q{query_id:<2} | ERRO"
                    )

                    self.registrar(
                        run=r,
                        query_id=query_id,
                        titulo=titulo,
                        categoria=categoria,
                        tempo_ms=tempo_ms,
                        num_tuplas=num_tuplas,
                        obs=erro[:150]
                    )

        print("\n================================================")
        print("[OK] COLETA FINALIZADA")
        print("================================================")

        print(f"CSV:")
        print(self.caminho_saida)

        print(f"\nMetadados:")
        print(self.caminho_metadados)
