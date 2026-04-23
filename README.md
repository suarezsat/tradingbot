# Backtester Forex

Aplicacion local de backtesting para estrategias de trading Forex construida con Python, Streamlit, `backtesting.py`, pandas, numpy y Plotly.

La app funciona completamente offline una vez instaladas las dependencias y esta pensada para cargar datos historicos reales en CSV o ZIP, ejecutar backtests, guardar resultados y entrenar lectura de mercado en modo manual.

## Que incluye esta version

- Selector inicial de versiones `1.0`, `1.1` y `1.3`.
- Version `1.0` con flujo clasico de un archivo y tres estrategias base.
- Version `1.1` con Inicio, Nuevo backtest y Guardados.
- Version `1.3` con:
  - backtesting avanzado
  - lector de graficas para trading manual
  - mas estrategias integradas
  - creador de estrategias personalizadas guardables
- Carga de archivos desde la interfaz y tambien desde una carpeta local configurada dentro de la app.
- Soporte para lotes multiarchivo con resultados individuales y resumen global comparativo.
- Guardado local de backtests para revisarlos despues.

## Estructura del proyecto

```text
tradingbot/
|-- app.py
|-- estrategias.py
|-- procesador_datos.py
|-- metricas.py
|-- almacen_backtests.py
|-- almacen_estrategias.py
|-- requirements.txt
|-- README.md
|-- assets/
|   `-- capturas/
|-- backtests_guardados/
`-- estrategias_guardadas/
```

## Requisitos previos

- Python 3.11 o superior
- `pip` disponible en la terminal
- Windows, macOS o Linux

## Instalacion paso a paso

### 1. Instalar Python

Si todavia no tienes Python:

1. Entra en [python.org/downloads](https://www.python.org/downloads/).
2. Instala una version 3.11 o superior.
3. En Windows, marca la opcion `Add Python to PATH` durante la instalacion.

Compruebalo con:

```powershell
python --version
```

### 2. Abrir la carpeta del proyecto

En PowerShell:

```powershell
cd C:\ruta\hasta\tradingbot
```

### 3. Instalar dependencias

Ejecuta:

```powershell
python -m pip install -r requirements.txt
```

### 4. Lanzar la aplicacion

Ejecuta:

```powershell
python -m streamlit run app.py
```

Ese es el comando recomendado en Windows para evitar problemas cuando `streamlit` no esta en el `PATH`.

## Uso rapido

1. Abre la app en el navegador.
2. Elige la version con la que quieres entrar.
3. En `Nuevo backtest`, selecciona archivos desde tu carpeta local o subelos manualmente.
4. Puedes mezclar varios `CSV`, `TXT` y `ZIP` compatibles en el mismo lote.
5. Elige una estrategia y ajusta parametros y gestion de riesgo.
6. Ejecuta el lote.
7. Revisa el resumen global y cada dataset en su propia pestana.
8. Si quieres, guarda el lote para recuperarlo despues en `Guardados`.

## Formatos de entrada compatibles

### HistData.com

- Columnas: `DateTime;Open;High;Low;Close;Volume`
- Fecha: `YYYYMMDD HHMMSS`
- Tambien soporta la variante sin cabecera.

### Dukascopy

- Columnas: `Time,Open,High,Low,Close,Volume`
- Fecha: `DD.MM.YYYY HH:MM:SS`

### MetaTrader (MT4/MT5)

- Columnas: `Date,Time,Open,High,Low,Close,Volume`
- Separador: coma o tabulacion

### ZIP

- La app puede abrir `.zip` directamente.
- Si dentro encuentra archivos `.csv` o `.txt` compatibles, los expande y procesa automaticamente.

## Estrategias incluidas

### Base de la version 1.0 y 1.1

- Cruce de Medias Moviles
- RSI con niveles
- Bollinger + RSI

### Estrategias extra de la version 1.3

- MACD clasico
- Donchian Breakout
- EMA + RSI tendencia
- Estocastico extremo
- Donchian + EMA
- RSI2 con tendencia
- Ruptura de sesion

## Estrategias personalizadas

La version `1.3` incluye una seccion `Estrategias` donde puedes:

- elegir una plantilla base
- ajustar sus parametros
- guardarla con nombre y descripcion
- reutilizarla luego en el backtester
- eliminarla cuando ya no la necesites

Las estrategias guardadas se almacenan localmente en `estrategias_guardadas/`.

## Trading manual

La version `1.3` incluye una vista `Trading manual` para:

- cargar un dataset unico desde carpeta local o subida manual
- avanzar vela a vela
- abrir compras y ventas manuales
- cerrar operaciones manualmente o por niveles
- revisar capital, curva de equity, drawdown y registro de trades

## Gestion de riesgo configurable

Desde la interfaz puedes ajustar:

- Stop Loss en pips
- Take Profit en pips
- Riesgo por operacion en porcentaje
- Capital inicial
- Maximo de operaciones abiertas
- Filtro horario por sesion
- Trailing stop

## Resultados y graficos

La app muestra:

- rentabilidad total
- numero total de operaciones
- win rate
- ratio riesgo/recompensa real
- drawdown maximo
- Sharpe Ratio
- Profit Factor
- mejor y peor operacion
- duracion media

Tambien dibuja:

- grafico de velas con entradas y salidas
- curva de equity
- grafico de drawdown
- histograma de resultados por operacion

## Guardados locales

- Los backtests guardados se almacenan en `backtests_guardados/`.
- Las estrategias personalizadas se almacenan en `estrategias_guardadas/`.
- Todo el flujo principal funciona sin conexion una vez hechas las instalaciones.

## Notas importantes

- El filtro por sesiones usa la hora del CSV tal como viene en el archivo y asume UTC.
- El tamano de pip se infiere automaticamente segun el precio medio del instrumento.
- La app esta pensada para Forex. Si pruebas otros mercados, revisa los resultados con criterio.
- Si el archivo tiene un formato invalido, la interfaz mostrara un mensaje de error claro.

## Comando exacto para arrancar

Desde la carpeta del proyecto, ejecuta exactamente:

```powershell
python -m streamlit run app.py
```

## Descarga masiva de HistData

El proyecto incluye un descargador para el catalogo `Generic ASCII / M1` de HistData:

```powershell
.\.venv\Scripts\python scripts\download_histdata_ascii_m1.py --root data\histdata_ascii_m1
```

Que hace:

- recorre los 66 instrumentos en el mismo orden que la web
- crea carpetas numeradas por par para conservar ese orden
- organiza por `anio/full_year` o `anio/months/MM_Month`
- descarga el ZIP
- descarga el archivo de estado
- extrae el CSV para poder usarlo directamente en la app
- genera inventarios `_inventory.json`, `_pair.json` y `_entry.json`

Ejemplos utiles:

```powershell
.\.venv\Scripts\python scripts\download_histdata_ascii_m1.py --inventory-only --root data\histdata_ascii_m1_catalog
.\.venv\Scripts\python scripts\download_histdata_ascii_m1.py --pairs EURUSD,GBPUSD --root data\histdata_ascii_m1_fxmajors
.\.venv\Scripts\python scripts\download_histdata_ascii_m1.py --pair-limit 3 --entry-limit-per-pair 2 --root data\histdata_ascii_m1_smoke
```

La carpeta `data/` esta ignorada por Git para no subir historicos masivos al repositorio.

## Investigacion de estrategias

El proyecto incluye un runner para buscar estrategias y parametros sobre los datos de HistData:

```powershell
.\.venv\Scripts\python scripts\optimize_forex_strategies.py --workers 4 --spread-pips 0.5 --screen-candidates 6 --deep-candidates 16 --report-name mi_investigacion
```

Que hace:

- lanza un cribado inicial de todas las estrategias integradas
- profundiza solo en las familias que mejor sobreviven
- aplica validacion walk-forward sobre varios años
- genera un informe Markdown reproducible
- guarda tambien los resultados completos en JSON

La ultima investigacion completa que se genero en este repo esta en:

```text
reports/strategy_research/full_research_spread05_20260423/
```

## Publicacion en Cloudflare

Este repo incluye configuracion para desplegar la app publica con Cloudflare Containers:

- `Dockerfile` para empaquetar la app Streamlit
- `wrangler.jsonc` para el Worker y el contenedor
- `src/index.js` como proxy publico hacia la instancia del contenedor
- `package.json` para instalar `wrangler` y `@cloudflare/containers`

### Desplegar en Cloudflare

1. Asegurate de tener Docker Desktop arrancado.
2. Instala las dependencias de Cloudflare:

```powershell
npm install
```

3. Comprueba tu sesion:

```powershell
npx wrangler whoami
```

4. Despliega:

```powershell
npx wrangler deploy
```

Al terminar, Cloudflare devolvera una URL publica `workers.dev` y el proyecto aparecera en el dashboard de `Workers & Pages`, incluyendo la vista de `Containers`.

### Requisito de plan

Cloudflare Containers requiere `Workers Paid plan`.

Si tu cuenta esta en plan gratuito:

- el repo ya queda preparado para Containers
- pero el despliegue gestionado no terminara hasta subir el plan
- mientras tanto puedes publicar la app temporalmente con Tunnel

### Publicacion temporal con Cloudflare Tunnel

Con la app corriendo en local:

```powershell
python -m streamlit run app.py
```

puedes exponerla publicamente con:

```powershell
npx wrangler tunnel quick-start http://127.0.0.1:8501
```

Eso devuelve una URL `trycloudflare.com` temporal que funciona mientras tu proceso local siga encendido.

### Importante sobre persistencia

La app original guarda backtests y estrategias en disco local. En Cloudflare Containers, el sistema de archivos del contenedor es efimero entre reinicios o despliegues.

Eso significa que:

- la web publica funciona
- la UI y el panel se pueden abrir desde Cloudflare
- pero los guardados hechos dentro del despliegue publico no estan garantizados a largo plazo

Si quieres que los backtests y estrategias guardadas persistan en la version publica, el siguiente paso es mover esa persistencia a servicios de Cloudflare como R2, D1 o KV.

### GitHub + Cloudflare

Una vez creado el Worker en Cloudflare:

1. Entra en `Workers & Pages`.
2. Abre el Worker `tradingbot`.
3. Ve a `Settings > Builds`.
4. Conecta el repositorio de GitHub `suarezsat/tradingbot`.

Cloudflare indica en su documentacion oficial que esa conexion permite despliegues automaticos en cada push al repositorio y comentarios/checks sobre builds en GitHub.
