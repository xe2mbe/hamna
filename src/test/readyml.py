import yaml

def get_fileNameMP3(yml_file,main_key,values_dict,find_key):
    # Cargar el archivo YAML
    with open(yml_file, 'r', encoding='utf-8') as archivo:
        datos = yaml.safe_load(archivo)
    alertas_dict = {alerta[values_dict]: alerta for alerta in datos[main_key]}
    #value_list = alertas_dict[value][list]
    find_value = alertas_dict.get(find_key)
    value = find_value['archivo']
    
    return value
# Cargar el archivo YAML
# with open('cfg.yml', 'r', encoding='utf-8') as archivo:
#     datos = yaml.safe_load(archivo)

# alertas_dict = {alerta['nombre']: alerta for alerta in datos['alertas']}

# alerta_continuamos = alertas_dict.get('continuamos')
#print(alerta_continuamos['nombre'],alerta_continuamos['archivo'])

test = get_fileNameMP3('cfg.yml','alertas','nombre','continuamos')

#print(test['continuamos']['nombre'],test['continuamos']['archivo'])

print(test)