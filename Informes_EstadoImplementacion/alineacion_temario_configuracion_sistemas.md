# Alineación del proyecto Elastic SIEM ADS-B con el temario de Configuración de Sistemas

## Resumen del contexto del proyecto
- El trabajo propone un laboratorio de Elastic Stack (Elasticsearch, Logstash, Kibana y Beats) como plataforma SIEM para centralizar emisiones ADS-B simuladas, documentado en `contexto.md` e `informe_entrega1.md`.
- La generación de datos se apoya en el backend `co-atc` (Go) y en el orquestador `simulador_bcn.py`, descritos en `trafico-simulado.md`, `diseno-red-vuelos-bcn.md`, `simulador_bcn.md` y `simulador_bcn_actualizacion.md`.
- La guía operativa `guia-implementacion-elastic-stack.md` detalla el despliegue con Docker Compose, pipelines de ingesta y reglas de detección para validar anomalías ADS-B.
- El foco académico es demostrar competencias de administración de sistemas: instalación y operación del stack, automatización de ingestión de datos, monitorización y documentación de incidencias.

## Correspondencias con el temario de la asignatura

### Bloque 1 · Instalación, administración básica y arranque
- `guia-implementacion-elastic-stack.md` cubre instalación y puesta en marcha de servicios Linux mediante Docker Compose, emulando tareas de arranque/parada de servicios (1.1, 1.2, 1.7).
- `simulador_bcn.md` y `simulador_bcn_actualizacion.md` documentan scripts operativos, ajustes de logging y banderas de ejecución, alineados con las tareas de administración básica posteriores a la instalación (1.3).

### Bloque 2 · Gestión de recursos y planificación
- El uso de volúmenes persistentes (`es_data`) y las recomendaciones de ILM/snapshots en `informe_entrega1.md` y `guia-implementacion-elastic-stack.md` abordan la gestión de almacenamiento y planificación del crecimiento de índices (2.1, 2.2).
- Las propuestas de copias de seguridad y retención mencionadas en `contexto.md` y `guiaConTemario.md` se conectan directamente con el temario de backups multinivel (2.3).

### Bloque 3 · Gestión de usuarios y autenticación
- La sección de seguridad del contexto (apartado 9 de `contexto.md`) plantea habilitar `xpack.security`, definir roles y controlar accesos en Kibana, cubriendo creación y administración de cuentas locales y controles de permisos (3.1, 3.2).
- La idea de integrar directorios externos para autenticación, adelantada en `guiaConTemario.md`, extiende la correspondencia hacia los contenidos de autenticación en red (4.2 del temario, tratado en este bloque en la guía docente).

### Bloque 4 · Configuración de red y recursos compartidos
- La arquitectura de ingestión descrita en `guia-implementacion-elastic-stack.md` configura servicios sobre puertos específicos (9200, 5601, 5044) y redes Docker, ejemplificando la configuración de red en equipos y servicios compartidos (4.1, 4.3).
- Los endpoints REST y WebSocket de `co-atc` usados por `simulador_bcn.py` muestran la administración de recursos de red y la coordinación entre servicios distribuidos.

### Bloque 5 · Servicios básicos
- El pipeline Filebeat → Logstash → Elasticsearch → Kibana constituye un laboratorio completo de servicios de red Linux, alineado con la gestión de servicios básicos del temario (5.3).
- Las recomendaciones de endurecimiento (firewall, monitoreo del stack y seguridad de Webhooks) en `contexto.md` y `informe_entrega1.md` abordan la temática de firewalls y protección de servicios (5.1).

### Bloque 6 · Migraciones y virtualización
- El despliegue con Docker Compose y la mención de contenerización y snapshots en `informe_entrega1.md` y `contexto.md` se vinculan con las secciones de virtualización y migración de servicios (6.3, 6.4).
- El plan de trabajo incluye reproducibilidad y restauración del laboratorio, aspectos clave en migraciones planificadas dentro de la asignatura.

## Ideas de refuerzo alineadas con el temario
1. **Crear unidades systemd para Elastic y Co-ATC**  
   Documentar `systemd` para arrancar/ detener `docker-compose` y el simulador refuerza el Bloque 1 (1.2, 1.7) mostrando control del arranque en Linux más allá de Docker.
2. **Implementar Snapshot Lifecycle Management (SLM) y políticas de cuotas**  
   Configurar un repositorio de snapshots (p. ej. MinIO) y políticas ILM documentadas conecta con el Bloque 2 (2.1, 2.3), demostrando planificación de crecimiento y copias de seguridad automatizadas.
3. **Habilitar `xpack.security` con roles diferenciados y autenticación externa**  
   Definir cuentas `admin`, `soc-analyst` y `viewer`, y opcionalmente integrar LDAP, cubre los contenidos del Bloque 3 y la autenticación en red del Bloque 4 (4.2).
4. **Diseñar segmentación de red y firewall para el laboratorio**  
   Crear redes Docker separadas (`ingesta`, `siem`, `simulador`) y establecer reglas `iptables`/`ufw` o `firewalld` para exponer solo Kibana y la API de Co-ATC refuerza los Bloques 4 (4.1) y 5 (5.1, 5.3).
5. **Documentar una migración controlada a otro host o entorno virtual**  
   Realizar un “lift & shift” del stack mediante snapshots y restauración en una VM remota (RHEL/AlmaLinux) cubre los resultados del Bloque 6 (6.1–6.4) y demuestra recuperación ante desastres.
6. **Añadir ingestión de eventos Windows mediante Winlogbeat**  
   Integra la perspectiva del temario sobre Windows Server (Bloque 1.W y 5.3) y amplía el SIEM para demostrar heterogeneidad de fuentes.

## Referencias teóricas sugeridas
- `TemarioCompletoTeoria.txt`, Bloques 1–6: guía docente oficial de Configuración de Sistemas.
- `contexto.md`: requisitos académicos del proyecto y lineamientos de seguridad/operación.
- `informe_entrega1.md`: diseño arquitectónico, planes de pruebas y riesgos.
- `guia-implementacion-elastic-stack.md`: despliegue y gobierno del stack Elastic.
- Documentación oficial de Elastic: *Configuring security for the Elastic Stack* y *Snapshot and Restore* (referenciadas en `guiaConTemario.md`).
