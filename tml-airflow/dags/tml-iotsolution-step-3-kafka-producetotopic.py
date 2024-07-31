from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

from datetime import datetime
from airflow.decorators import dag, task

######################################## USER CHOOSEN PARAMETERS ########################################
default_args = {
  'owner' : 'Sebastian Maurice',    
  'enabletls': 1,
  'microserviceid' : '',
  'producerid' : 'iotsolution',  
  'topics' : 'iot-raw-data', # *************** This is one of the topic you created in SYSTEM STEP 2
  'identifier' : 'TML solution',  
  'start_date': datetime (2024, 6, 29),
  'retries': 1,
    
}

######################################## USER CHOOSEN PARAMETERS ########################################

######################################## START DAG AND TASK #############################################

# Instantiate your DAG
@dag(dag_id="tml_iotsolution_step_3_kafka_producetotopic_dag", default_args=default_args, tags=["tml-iotsolution-step-3-kafka-producetotopic"], schedule=None,catchup=False)
def startproducingtotopic():
  # This sets the lat/longs for the IoT devices so it can be map
  VIPERTOKEN=""
  VIPERHOST=""
  VIPERPORT=""
    
  def csvlatlong(filename):
    csvfile = open(filename, 'r')

    fieldnames = ("dsn","oem","identifier","index","lat","long")
    lookup_dict = {}

    reader = csv.DictReader( csvfile, fieldnames)
    for row in reader:
        lookup_dict[(row['dsn'], row['lat'].lower(),
                    row['long'].lower(),row['identifier'])] = row

    return lookup_dict

  def getlatlong(reader,search,key):
    i=0
    locations = [i for i, t in enumerate(reader) if t[0]==search]
    value_at_index = list(reader.values())[locations[0]]
  
    return value_at_index['lat'],value_at_index['long'],value_at_index['identifier']

  def getlatlong2(reader):
    random_lines=random.choice(list(reader))
    return random_lines[1],random_lines[2],random_lines[0]

  def producetokafka(value, tmlid, identifier,producerid,maintopic,substream,args):
     inputbuf=value     
     topicid=-999
  
     # Add a 7000 millisecond maximum delay for VIPER to wait for Kafka to return confirmation message is received and written to topic 
     delay=7000
     enabletls = args['enabletls']
     identifier = args['identifier']

     try:
        result=maadstml.viperproducetotopic(VIPERTOKEN,VIPERHOST,VIPERPORT,maintopic,producerid,enabletls,delay,'','', '',0,inputbuf,substream,
                                            topicid,identifier)
     except Exception as e:
        print("ERROR:",e)

  @task(task_id="gettmlsystemsparams")         
  def gettmlsystemsparams():
    VIPERTOKEN = ti.xcom_pull(dag_id='tml_system_step_1_getparams_dag',task_ids='getparams',key="VIPERTOKEN")
    VIPERHOST = ti.xcom_pull(dag_id='tml_system_step_1_getparams_dag',task_ids='getparams',key="VIPERHOST")
    VIPERPORT = ti.xcom_pull(dag_id='tml_system_step_1_getparams_dag',task_ids='getparams',key="VIPERPORT")
    
    return [VIPERTOKEN,VIPERHOST,VIPERPORT]
        
  @task(task_id="readdata")        
  def readdata(params):
      args = default_args    
      basedir = '/'  
      inputfile=basedir + '/IotSolution/IoTData.txt'

      # MAin Kafka topic to store the real-time data
      maintopic = args['topics']
      producerid = args['producerid']
    
      reader=csvlatlong(basedir + '/IotSolution/dsntmlidmain.csv')
 
      k=0

      file1 = open(inputfile, 'r')
      print("Data Producing to Kafka Started:",datetime.datetime.now())

      while True:
        line = file1.readline()
        line = line.replace(";", " ")
        # add lat/long/identifier
        k = k + 1
        try:
          if not line or line == "":
            #break
            file1.seek(0)
            k=0
            print("Reached End of File - Restarting")
            print("Read End:",datetime.datetime.now())
            continue

          jsonline = json.loads(line)
          lat,long,ident=getlatlong(reader,jsonline['metadata']['dsn'],'dsn')
          line = line[:-2] + "," + '"lat":' + lat + ',"long":'+long + ',"identifier":"' + ident + '"}'

          producetokafka(line.strip(), "", "",producerid,maintopic,"",args)
          # change time to speed up or slow down data   
          time.sleep(0.15)
        except Exception as e:
          print(e)  
          pass  
  
      file1.close()
    
  readdata(gettmlsystemsparams())
    

dag = startproducingtotopic()
