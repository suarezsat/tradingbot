# Backtester Forex

Aplicacion local de backtesting para estrategias de trading Forex construida con Python, Streamlit, `backtesting.py`, pandas, numpy y Plotly.

## Que hace esta app

- Carga archivos CSV, TXT y ZIP desde la interfaz.
- Permite seleccionar archivos directamente desde una carpeta local dentro de la app.
- Detecta automaticamente formatos de HistData.com, Dukascopy y MetaTrader.
- Expande ZIP compatibles de forma automatica.
- Ejecuta backtests con 3 estrategias incluidas.
- Procesa varios archivos en un mismo lote.
- Muestra resultados individuales por archivo y un resumen comparativo final.
- Guarda lotes de backtesting en local para consultarlos despues.
- Permite ajustar stop loss, take profit, riesgo por operacion, trailing stop, capital inicial, numero maximo de operaciones y filtro horario por sesion.
- Muestra metricas de rendimiento y graficos interactivos.
- Funciona completamente offline una vez instaladas las dependencias.

## Estructura del proyecto

```text
backtester_forex/
├── app.py
├── estrategias.py
├── procesador_datos.py
├── metricas.py
├── requirements.txt
└── README.md
```

## Requisitos previos

- Windows, macOS o Linux
- Python 3.11 o superior
- `pip` disponible en la terminal

## Instalacion paso a paso

### 1. Instalar Python

Si no tienes Python instalado:

1. Ve a la pagina oficial de Python: https://www.python.org/downloads/
2. Descarga una version 3.11 o superior.
3. Durante la instalacion, marca la opcion **Add Python to PATH**.
4. Termina la instalacion y cierra el instalador.

Para comprobarlo, abre una terminal y ejecuta:

```bash
python --version
```

### 2. Abrir una terminal en la carpeta del proyecto

Colocate dentro de la carpeta `backtester_forex`.

Ejemplo en Windows PowerShell:

```powershell
cd C:\ruta\hasta\backtester_forex
```

### 3. Instalar dependencias

Ejecuta este comando:

```bash
pip install -r requirements.txt
```

Esto instalara todo lo necesario para usar la aplicacion sin internet despues.

### 4. Lanzar la aplicacion

Ejecuta:

```bash
streamlit run app.py
```

Se abrira una app local en tu navegador.

## Uso rapido

1. Abre la app.
2. En la pestana **Nuevo backtest**, elige archivos desde la carpeta local o subelos manualmente.
3. Puedes mezclar varios CSV y ZIP en el mismo lote.
4. Elige una de las 3 estrategias disponibles.
5. Ajusta los parametros de la estrategia y la gestion de riesgo.
6. Pulsa **Ejecutar lote de backtesting**.
7. Revisa el **Resumen global** y las pestanas individuales de cada archivo.
8. Si quieres, guarda el lote para verlo despues en la pestana **Guardados**.

## Formatos CSV compatibles

### HistData.com

- Columnas: `DateTime;Open;High;Low;Close;Volume`
- Fecha: `YYYYMMDD HHMMSS`
- Tambien se soporta la variante sin cabecera que empieza directamente con las velas.

### Dukascopy

- Columnas: `Time,Open,High,Low,Close,Volume`
- Fecha: `DD.MM.YYYY HH:MM:SS`

### MetaTrader (MT4/MT5)

- Columnas: `Date,Time,Open,High,Low,Close,Volume`
- Separador: tabulacion o coma

### ZIP

- Puedes subir o seleccionar archivos `.zip`.
- La app buscara dentro del ZIP archivos `.csv` o `.txt` compatibles y los procesara automaticamente.

## Estrategias incluidas

### 1. Cruce de Medias Moviles

- Compra: EMA rapida cruza hacia arriba la EMA lenta
- Venta: EMA rapida cruza hacia abajo la EMA lenta

### 2. RSI con niveles

- Compra: RSI cruza hacia arriba el nivel de sobreventa
- Venta: RSI cruza hacia abajo el nivel de sobrecompra

### 3. Bollinger + RSI

- Compra: el precio toca la banda inferior y el RSI esta por debajo de 40
- Venta: el precio toca la banda superior y el RSI esta por encima de 60

## Notas importantes

- El filtro por sesiones usa la hora del CSV tal como viene en el archivo y asume que esta en UTC.
- El tamano de pip se infiere automaticamente segun el precio medio del instrumento.
- La app esta pensada para pares Forex. Si usas instrumentos no Forex o cruces exoticos, revisa los resultados con criterio.
- Si el CSV tiene un formato invalido, la interfaz mostrara un mensaje claro con el problema detectado.
- Los backtests guardados se almacenan en la carpeta `backtests_guardados`.

## Comando para lanzar la app

Desde la carpeta `backtester_forex`, ejecuta:

```bash
streamlit run app.py
```
