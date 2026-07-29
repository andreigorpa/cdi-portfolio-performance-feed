import json
import os
import urllib.request
from datetime import datetime, timedelta

def buscar_dados_api(data_inicio, data_fim):
  
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.11/dados?formato=json&dataInicial={data_inicio}&dataFinal={data_fim}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        print(f"Erro ao acessar API do BCB: {e}")
        return []

def atualizar_cdi():
    nome_arquivo = 'cdi_acumulado.json'
    
    # Se o arquivo não existir, faz a carga histórica completa inicial
    if not os.path.exists(nome_arquivo):
        print("Arquivo não encontrado. Iniciando carga histórica completa (Últimos 10 anos)...")
        data_fim_historico = datetime.now().strftime("%d/%m/%Y")
        data_ini_historico = (datetime.now() - timedelta(days=365 * 10 - 1)).strftime("%d/%m/%Y")
        
        dados_api = buscar_dados_api(data_ini_historico, data_fim_historico)
        if not dados_api:
            print("Não foi possível carregar o histórico.")
            return

        json_pp = []
        fator_acumulado = 1.000000
        
        for registro in dados_api:
            partes = registro['data'].split('/')
            data_iso = f"{partes[2]}-{partes[1]}-{partes[0]}"
            taxa_diaria = float(registro['valor'].replace(',', '.'))
            fator_acumulado *= (1 + (taxa_diaria / 100))
            
            json_pp.append({
                "date": data_iso,
                "close": round(fator_acumulado * 100, 6),
                "fator_interno": fator_acumulado # Salva o fator bruto para o cálculo composto do dia seguinte
            })
            
        with open(nome_arquivo, 'w') as f:
            json.dump(json_pp, f, indent=2)
        print("Carga histórica concluída com sucesso!")
        return

    # Se o arquivo já existe, faz a atualização incremental (apenas o dia/dias novos)
    with open(nome_arquivo, 'r') as f:
        json_pp = json.load(f)
        
    if not json_pp:
        print("O arquivo existente está vazio.")
        return

    # Identifica o último dia registrado e o último fator acumulado histórico
    ultimo_registro = json_pp[-1]
    ultima_data_str = ultimo_registro['date'] # Formato YYYY-MM-DD
    fator_acumulado = ultimo_registro.get('fator_interno', ultimo_registro['close'] / 100)
    
    ultima_data_dt = datetime.strptime(ultima_data_str, "%Y-%m-%d")
    data_amanha_dt = ultima_data_dt + timedelta(days=1)
    
    # Se a última data gravada for hoje ou futura, não precisa atualizar nada
    if data_amanha_dt > datetime.now():
        print("O arquivo já está totalmente atualizado com os dados mais recentes.")
        return

    data_inicial_busca = data_amanha_dt.strftime("%d/%m/%Y")
    data_final_busca = datetime.now().strftime("%d/%m/%Y")
    
    print(f"Buscando atualizações de {data_inicial_busca} até {data_final_busca}...")
    novos_dados_api = buscar_dados_api(data_inicial_busca, data_final_busca)
    
    if not novos_dados_api:
        print("Nenhum dado novo encontrado na API para os dias úteis recentes.")
        return

    novos_registros = 0
    for registro in novos_dados_api:
        partes = registro['data'].split('/')
        data_iso = f"{partes[2]}-{partes[1]}-{partes[0]}"
        
        # Evita duplicar o mesmo dia caso a API traga algo repetido
        if any(item['date'] == data_iso for item in json_pp):
            continue
            
        taxa_diaria = float(registro['valor'].replace(',', '.'))
        fator_acumulado *= (1 + (taxa_diaria / 100))
        
        json_pp.append({
            "date": data_iso,
            "close": round(fator_acumulado * 100, 6),
            "fator_interno": fator_acumulado
        })
        novos_registros += 1

    if novos_registros > 0:
        with open(nome_arquivo, 'w') as f:
            json.dump(json_pp, f, indent=2)
        print(f"Sucesso: {novos_registros} novo(s) dia(s) adicionado(s) ao arquivo!")
    else:
        print("Nenhum registro inédito para anexar.")

if __name__ == "__main__":
    atualizar_cdi()
