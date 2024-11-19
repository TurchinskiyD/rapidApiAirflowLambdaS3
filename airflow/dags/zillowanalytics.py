
import os
import json
import requests
from airflow import DAG
from datetime import timedelta, datetime
from airflow.operators.python import PythonOperator
from airflow.operators.bash_operator import BashOperator



# Отримуємо шлях до файлу конфігурації відносно розташування DAG
dag_folder = os.path.dirname(os.path.realpath(__file__))  # Директорія файлу DAG
config_file_path = os.path.join(dag_folder, "../config_api.json")  # Вказуємо шлях до JSON

if not os.path.exists(config_file_path):
    raise FileNotFoundError(f"Файл конфігурації не знайдено: {config_file_path}")



with open(config_file_path, 'r') as config_file:
    api_host_key = json.load(config_file)


now = datetime.now()
dt_now_string = now.strftime("%d%m%Y%H%M%S")

def extract_zillow_data(**kwargs):
    url = kwargs['url']
    headers = kwargs['headers']
    querystring = kwargs['querystring']
    data_string = kwargs['data_string']

    response = requests.get(url, headers=headers, params = querystring)
    response_data = response.json()

    output_file_path = f'/home/ubuntu/response_data_{data_string}.json'
    file_str = f'response_data_{data_string}.csv'

    with open(output_file_path, 'w') as output_file:
        json.dump(response_data, output_file, indent = 4)
    output_list = [output_file_path, file_str]
    return output_list




default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 11, 18),
    'email': ['myemail@domain.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(seconds=15)
}


with DAG('zillow_analitics_dag',
        default_args = default_args,
        schedule_interval = '@daily',
        catchup = False) as dag:

        extract_zillow_data_var = PythonOperator(
            task_id= 'task_extract_zillow_data_var',
            python_callable=extract_zillow_data,
            op_kwargs={ 'url': 'https://zillow56.p.rapidapi.com/search',
                    'querystring': {"location":"houston, tx","output":"json","status":"forSale","sortSelection":"priorityscore","listing_type":"by_agent","doz":"any"},
                    'headers': api_host_key,
                    'data_string': dt_now_string
            }
        )

        load_to_s3 = BashOperator(
            task_id = 'task_load_to_s3',
            bash_command = 'aws s3 mv {{ ti.xcom_pull("task_extract_zillow_data_var")[0]}} s3://landing-rapidapiairflowlambda/',
        )


        extract_zillow_data_var >> load_to_s3