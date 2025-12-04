# Guía de Implementación: Elastic Stack SIEM para Simulación ADS-B

Este documento sirve como una guía paso a paso para implementar la solución Elastic Stack (SIEM) descrita en `contexto.md`. El objetivo es centralizar, analizar y detectar anomalías en los datos de tráfico aéreo generados por el simulador `simulador_bcn.py` y el backend `co-atc`.

## Implementación en este repo (archivos ya listos)
- `docker-compose.yml`: levanta Elasticsearch, Kibana, Logstash y Filebeat (Elastic 8.11.1, sin seguridad, un nodo).
- `filebeat.yml`: lee `logs/co_atc.log` (JSON por línea) y las envía a Logstash. Añade nuevas fuentes según la API externa que integres.
- `logstash/pipeline/adsb.conf`: input Beats 5044, conversión de tipos, geo_point `[location]`, parseo de `timestamp` ISO8601 y envío a índice `adsb-data-*` + stdout.
- Arranque rápido (desde la raíz del proyecto):
  ```bash
  docker-compose up -d
  docker-compose logs -f filebeat logstash
  ```
- Requisitos: tener `logs/*.log` con líneas JSON (idealmente cada mensaje ADS-B). Los contenedores leen `/home/.../ADS-B_SIEM/logs` montado en `/logs`.

## Generación de logs ADS-B
- Ahora no hay inyector local; deberás apuntar Filebeat/Logstash a la fuente que definas (API externa o feed que escriba JSON en `logs/`).
- Conserva el pipeline y mapeos para lat/lon/alt/speed/heading/vertical_rate; adapta el campo `source` o `anomaly_flags` según lo que emitas.

## Arquitectura General

El flujo de datos seguirá el siguiente esquema:

```
[simulador_bcn.py] -> [co-atc API] -> [Logs de co-atc] -> [Filebeat] -> [Logstash] -> [Elasticsearch] -> [Kibana]
```

1.  **`simulador_bcn.py`**: Orquesta el escenario de vuelo, creando y moviendo aeronaves a través de la API de `co-atc`.
2.  **`co-atc`**: Expone los datos de las aeronaves (simuladas y reales) a través de sus logs o endpoints.
3.  **Filebeat**: Agente ligero que recolecta los logs generados por `co-atc`.
4.  **Logstash**: Procesa, enriquece y normaliza los datos recibidos de Filebeat antes de enviarlos a Elasticsearch.
5.  **Elasticsearch**: Almacena, indexa y permite la búsqueda de todos los datos de vuelo. Es el núcleo del SIEM.
6.  **Kibana**: Interfaz web para visualizar los datos en dashboards, explorar la información y configurar las reglas de detección de anomalías del SIEM.

---

## Fase 1: Despliegue del Núcleo de Elastic Stack

El primer paso es levantar los componentes principales: Elasticsearch y Kibana. Usaremos Docker Compose para una gestión sencilla.

1.  **Crear el fichero `docker-compose.yml`**:
    En la raíz de tu proyecto, crea un fichero `docker-compose.yml` con el siguiente contenido:

    ```yaml
    version: '3.8'
    services:
      elasticsearch:
        image: docker.elastic.co/elasticsearch/elasticsearch:8.11.1
        container_name: elasticsearch
        environment:
          - discovery.type=single-node
          - xpack.security.enabled=false # Deshabilitado para simplificar el entorno académico
          - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
        ports:
          - "9200:9200"
        volumes:
          - es_data:/usr/share/elasticsearch/data

      kibana:
        image: docker.elastic.co/kibana/kibana:8.11.1
        container_name: kibana
        ports:
          - "5601:5601"
        environment:
          - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
        depends_on:
          - elasticsearch

    volumes:
      es_data:
        driver: local
    ```

2.  **Iniciar los servicios**:
    Abre un terminal en el directorio donde guardaste el `docker-compose.yml` y ejecuta:
    ```bash
    docker-compose up -d
    ```

3.  **Verificación**:
    *   Accede a `http://localhost:9200` en tu navegador. Deberías ver una respuesta JSON de Elasticsearch.
    *   Accede a `http://localhost:5601`. Deberías ver la interfaz de Kibana cargándose.

---

## Fase 2: Configuración de la Ingesta de Datos (Filebeat y Logstash)

Ahora configuraremos cómo los datos del simulador llegarán a Elasticsearch. Usaremos Filebeat para leer los logs de `co-atc` y Logstash para procesarlos.

1.  **Adaptar `co-atc` para que genere logs útiles**:
    Asegúrate de que `co-atc` escribe los datos de las aeronaves a un fichero de log en formato JSON. Si no lo hace por defecto, la opción más sencilla es modificar el bucle de `UpdatePositions` en `internal/adsb/service.go` para que escriba cada estado de aeronave en un fichero `logs/traffic.log`.

2.  **Añadir Filebeat y Logstash al `docker-compose.yml`**:

    ```yaml
    # ... (servicios de elasticsearch y kibana) ...

      filebeat:
        image: docker.elastic.co/beats/filebeat:8.11.1
        container_name: filebeat
        user: root # Necesario para acceder a los logs de otros contenedores o del host
        volumes:
          - ./filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
          - /var/lib/docker/containers:/var/lib/docker/containers:ro # Monta los logs de Docker
          - /var/run/docker.sock:/var/run/docker.sock # Para metadatos de contenedores
        depends_on:
          - logstash

      logstash:
        image: docker.elastic.co/logstash/logstash:8.11.1
        container_name: logstash
        ports:
          - "5044:5044"
        volumes:
          - ./logstash/pipeline/:/usr/share/logstash/pipeline/
        depends_on:
          - elasticsearch
    ```

3.  **Configurar Filebeat (`filebeat.yml`)**:
    Crea un fichero `filebeat.yml` para indicarle que lea los logs de `co-atc` (o su salida estándar si corre en Docker) y los envíe a Logstash.

    ```yaml
    filebeat.inputs:
    - type: container
      paths:
        - /var/lib/docker/containers/*/*.log
      processors:
        - add_docker_metadata: ~

    output.logstash:
      hosts: ["logstash:5044"]
    ```

4.  **Configurar el Pipeline de Logstash**:
    Crea un directorio `logstash/pipeline/` y dentro un fichero `adsb.conf`. Este pipeline procesará los datos.

    ```conf
    input {
      beats {
        port => 5044
      }
    }

    filter {
      # Asumimos que el log de co-atc es un JSON en el campo 'message'
      json {
        source => "message"
      }

      # Convierte los campos a sus tipos correctos
      mutate {
        convert => { "altitude" => "integer" }
        convert => { "speed" => "integer" }
        convert => { "lat" => "float" }
        convert => { "lon" => "float" }
      }

      # Crea un campo geo_point para los mapas de Kibana
      mutate {
        add_field => { "[location][lat]" => "%{lat}" }
        add_field => { "[location][lon]" => "%{lon}" }
      }
    }

    output {
      elasticsearch {
        hosts => ["http://elasticsearch:9200"]
        index => "adsb-data-%{+YYYY.MM.dd}"
      }
    }
    ```

5.  **Reiniciar Docker Compose**:
    ```bash
    docker-compose up -d --build
    ```

---

## Fase 3: Visualización en Kibana

Con los datos fluyendo hacia Elasticsearch, es hora de visualizarlos.

1.  **Crear un Data View**:
    *   En Kibana, ve a `Management > Stack Management > Data Views`.
    *   Crea un nuevo Data View con el patrón `adsb-data-*`.
    *   Selecciona `@timestamp` como el campo de tiempo.

2.  **Explorar los datos**:
    *   Ve a la pestaña `Discover`. Deberías ver los eventos de tus vuelos simulados llegando en tiempo real.

3.  **Crear un Dashboard**:
    *   Ve a `Dashboard` y crea uno nuevo.
    *   Añade visualizaciones ("Lens" o "Visualize Library"):
        *   **Mapa**: Usa el tipo `Maps` y configura una capa con el índice `adsb-data-*` y el campo `location` que creamos en Logstash.
        *   **Gráfico de Series Temporales**: Muestra la `cantidad de vuelos únicos` (Cardinality de `hex.keyword`) a lo largo del tiempo.
        *   **Indicador (Metric)**: Muestra la altitud media o la velocidad máxima actual.
        *   **Tabla de Datos**: Lista los vuelos activos con sus datos más relevantes (icao, altitud, velocidad, rumbo).

---

## Fase 4: Detección de Anomalías con Elastic Security

Esta es la parte central de tu proyecto SIEM.

1.  **Acceder a Elastic Security**:
    *   En el menú de Kibana, ve a `Security > Detections`.

2.  **Crear Reglas de Detección Personalizadas**:
    *   Ve a `Manage > Rules` y haz clic en `Create new rule`.
    *   **Tipo de Regla**: `Custom query`.
    *   **Índice**: `adsb-data-*`.

    **Ejemplo de Regla 1: Altitud Negativa**
    *   **Nombre**: `ADS-B Anomaly - Negative Altitude`
    *   **Custom query**: `altitude < 0`
    *   **Severidad**: `High`
    *   **Acciones**: Configura una acción, como `Index` para escribir la alerta en un índice `.siem-signals-*`.

    **Ejemplo de Regla 2: Velocidad Imposible**
    *   **Nombre**: `ADS-B Anomaly - Impossible Speed`
    *   **Custom query**: `speed > 1200` (o el umbral que definiste en `diseno-red-vuelos-bcn.md`)
    *   **Severidad**: `Critical`

    **Ejemplo de Regla 3: Duplicado de ICAO (más compleja)**
    *   **Tipo de Regla**: `Threshold`.
    *   **Agrupar por**: `hex.keyword`.
    *   **Condición**: `count()` de documentos es `> 1` en un intervalo de tiempo corto (ej. 10 segundos). Esto puede generar falsos positivos, pero es un buen punto de partida.

3.  **Probar las Reglas**:
    *   Ejecuta tu `simulador_bcn.py` con la opción `--incluir-anomalias`.
    *   Ve a la página de `Detections` en Kibana. Deberías ver las alertas generándose a medida que el simulador inyecta los datos anómalos.
    *   Analiza las alertas y usa la `Timeline` para investigar los eventos que las causaron.

---

## Siguientes Pasos

Con esta base, puedes expandir el proyecto:

*   **Implementar la acción de "quitar avión"**: Desarrolla el webhook que discutimos, que añade un ICAO a un índice `blacklist`. Modifica el pipeline de Logstash para que descarte los mensajes de los ICAO en esa lista negra.
*   **Usar Machine Learning**: Explora las funciones de "Anomaly Detection" de Elastic para que el sistema aprenda qué es un comportamiento normal y detecte desviaciones automáticamente, sin necesidad de reglas manuales.
*   **Mejorar los Dashboards**: Crea dashboards específicos para el análisis forense de incidentes, mostrando toda la información relevante de una alerta.

Esta guía te proporciona una estructura sólida y directamente aplicable a los ficheros y la lógica que ya has desarrollado. ¡Mucho éxito con la implementación!
