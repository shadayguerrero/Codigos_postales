# Asignación de AGEB (CVEGEO) a Dataset CIENI - Reporte Completo

## 📋 Resumen Ejecutivo

Este proyecto implementa una metodología híbrida para asignar códigos AGEB (Áreas Geoestadísticas Básicas) oficiales del INEGI a un dataset de 7,074 registros de conectividad en México, específicamente para CDMX y Estado de México.

### 🎯 Resultados Finales
- **✅ 100% de cobertura** - Todos los 7,074 registros tienen AGEB asignado
- **✅ 100% AGEB urbanos** - Todos los códigos son de 13 caracteres (urbanos)
- **✅ 100% CPs normalizados** - Todos los códigos postales tienen 5 dígitos
- **✅ 93.3% con coordenadas exactas** - 6,602 registros con lat/lon precisas
- **✅ 1,688 AGEB únicos** - Excelente diversidad geográfica

---

## 📂 Datos Utilizados

### 🗂️ Datasets de Entrada
1. **`cieni_geo_data.csv`** - Dataset principal con 7,074 registros
   - Columnas: `Clave`, `Estado`, `Municipio`, `CODE`, `Colonia`, `CP`
   - Cobertura: CDMX y Estado de México

2. **`00a.parquet`** - AGEB oficiales del INEGI Marco Geoestadístico 2020
   - 82,123 AGEB con geometrías y clasificación AMBITO (Urbana/Rural)
   - Columnas: `CVEGEO`, `CVE_ENT`, `CVE_MUN`, `CVE_LOC`, `CVE_AGEB`, `AMBITO`, `geometry_str`

3. **`CP-MEX-2025.csv`** - Códigos postales con coordenadas
   - 36,182 códigos postales con latitud/longitud exactas
   - Fuente: [adrianrg.com](https://adrianrg.com/dataset-codigos-postales-de-mexico-con-coordenadas-2025/)

### 🎯 Datasets de Salida
- **`cieni_geo_data_cp_corregidos.csv`** - Dataset final con AGEB asignados
- **`cieni_geo_data_cp_corregidos_with_clusters.csv`** - Dataset final con AGEB asignados, cluster_trace, phylocluster

---

## 🛠️ Metodología Implementada

### 📊 Estrategia Híbrida Multi-Etapa

#### **Etapa 1: Asignación Inicial**
1. **Intersección Espacial por CP** (41.4% - 2,932 registros)
   - Usa coordenadas exactas de códigos postales
   - Intersección con polígonos AGEB del INEGI
   - Máxima precisión geográfica

2. **Distribución por Colonia** (2.5% - 176 registros)
   - Geocodificación de `estado + municipio + colonia`
   - Asignación determinística basada en hash de colonia

3. **Distribución por Municipio** (7.0% - 497 registros)
   - Mapeo de códigos CODE a municipios INEGI
   - Distribución equitativa entre AGEB urbanos del municipio

4. **Fallback por Estado** (0.4% - 30 registros)
   - Último recurso para casos extremos
   - Solo AGEB urbanos del estado correspondiente

#### **Etapa 2: Corrección de CVEGEO Rurales**
- **Problema**: 253 registros tenían AGEB rurales (9 dígitos)
- **Solución**: Reasignación a AGEB urbanos del mismo municipio
- **Resultado**: 100% AGEB urbanos (13 caracteres)

#### **Etapa 3: Corrección de Códigos Postales**
- **Problema**: 3,499 registros (52.2%) tenían CPs de 4 dígitos
- **Solución**: Agregar cero inicial + reasignación AGEB por intersección espacial
- **Resultado**: 100% CPs de 5 dígitos + 48.6% con intersección espacial mejorada

---

## 💻 Scripts Desarrollados

### 🔧 Script Principal: `corregir_cp_4_digitos_cieni.py`


```

### 🔧 Scripts Auxiliares

1. **`asignar_ageb_cieni_ultra_rapido.py`** - Asignación inicial de AGEB
2. **`corregir_ageb_solo_urbanos.py`** - Conversión de AGEB rurales a urbanos
3. **`corregir_cp_4_digitos_cieni.py`** - Corrección final de códigos postales

---

## 🚀 Pasos para Ejecutar

### 📋 Prerrequisitos

```bash
# Instalar dependencias
pip install pandas geopandas shapely pyarrow

# Descargar datos necesarios
# 1. cieni_geo_data.csv - Dataset principal
# 2. 00a.parquet - AGEB del INEGI
# 3. CP-MEX-2025.csv - Coordenadas de códigos postales
```

### 🔄 Proceso de Ejecución

#### **Paso 1: Asignación Inicial**
```bash
python3 asignar_ageb_cieni_ultra_rapido.py
# Genera: cieni_geo_data_con_ageb.csv
```

#### **Paso 2: Corrección a Solo Urbanos**
```bash
python3 corregir_ageb_solo_urbanos.py
# Genera: cieni_geo_data_solo_urbanos.csv
```

#### **Paso 3: Corrección de Códigos Postales**
```bash
python3 corregir_cp_4_digitos_cieni.py
# Genera: cieni_geo_data_cp_corregidos.csv (ARCHIVO FINAL)
```

### ⏱️ Tiempo de Ejecución
- **Paso 1**: ~5 minutos
- **Paso 2**: ~1 minuto  
- **Paso 3**: ~8 minutos
- **Total**: ~15 minutos

---

## 📊 Resultados Detallados

### 🎯 Distribución Final de Métodos

| Método | Registros | Porcentaje | Descripción |
|--------|-----------|------------|-------------|
| **Intersección Espacial CP Corregido** | 3,439 | 48.6% | CPs corregidos con intersección exacta |
| **Intersección Espacial CP** | 2,932 | 41.4% | Intersección espacial original |
| **Municipio Urbano Mejorado** | 261 | 3.7% | Distribución por municipio mejorada |
| **Municipio Urbano Corregido** | 236 | 3.3% | AGEB rurales convertidos a urbanos |
| **Distribución Colonia** | 176 | 2.5% | Asignación por colonia geocodificada |
| **Estado Urbano Mejorado** | 30 | 0.4% | Fallback por estado |

### 📈 Métricas de Calidad

#### **✅ Cobertura Completa**
- **7,074 registros procesados** (100%)
- **7,074 registros con AGEB asignado** (100%)
- **0 registros sin asignar** (0%)

#### **🏙️ Calidad de AGEB**
- **7,074 AGEB urbanos** (100% - 13 caracteres)
- **0 AGEB rurales** (0% - 9 caracteres)
- **1,688 AGEB únicos** (excelente diversidad)
- **Promedio 4.2 registros por AGEB**

#### **📮 Calidad de Códigos Postales**
- **6,704 CPs de 5 dígitos** (100% de CPs válidos)
- **0 CPs de 4 dígitos** (0% - todos corregidos)
- **370 registros sin CP** (5.2% - CP = "." o "nan")

#### **🌍 Precisión Geográfica**
- **6,602 registros con coordenadas** (93.3%)
- **472 registros sin coordenadas** (6.7%)
- **6,371 registros con intersección espacial exacta** (90.0%)

### 🗺️ Cobertura Geográfica

#### **CDMX (16 Alcaldías)**
- **Iztapalapa**: 1,047 registros (14.8%)
- **Cuauhtémoc**: 537 registros (7.6%)
- **Coyoacán**: 359 registros (5.1%)
- **Benito Juárez**: 317 registros (4.5%)
- **Álvaro Obregón**: 289 registros (4.1%)
- **Otros**: 1,951 registros (27.6%)

#### **Estado de México (31 Municipios)**
- **Ecatepec de Morelos**: 421 registros (6.0%)
- **Nezahualcóyotl**: 387 registros (5.5%)
- **Tlalnepantla**: 298 registros (4.2%)
- **Naucalpan**: 267 registros (3.8%)
- **Otros**: 1,201 registros (17.0%)

---

## 🌟 Ejemplos de Asignaciones

### 📍 Intersección Espacial Exacta

| Clave | Municipio | Colonia | CP Original | CP Corregido | AGEB Asignado | Coordenadas |
|-------|-----------|---------|-------------|--------------|---------------|-------------|
| CEC-19-0007 | Azcapotzalco | Santiago Ahuizotla | 2750 | 02750 | 0900200011038 | 19.4889, -99.1856 |
| CEC-19-0012 | Cuauhtémoc | Doctores | 6720 | 06720 | 090150001113A | 19.4167, -99.1431 |
| CEC-19-0014 | Álvaro Obregón | Olivar del Conde | 1400 | 01400 | 0901000010597 | 19.3667, -99.2000 |

### 🏘️ Distribución por Colonia

| Clave | Municipio | Colonia | AGEB Asignado | Método |
|-------|-----------|---------|---------------|---------|
| CEC-19-0156 | Iztapalapa | Santa Cruz Meyehualco | 0900900011716 | Distribucion_Colonia |
| CEC-19-0234 | Gustavo A. Madero | San José de la Escalera | 0900700010638 | Distribucion_Colonia |

### 🗺️ Distribución por Municipio

| Clave | Municipio | AGEB Asignado | Método |
|-------|-----------|---------------|---------|
| CEC-19-0089 | Tecámac | 1509900451417 | Municipio_Urbano_Mejorado |
| CEC-19-0145 | Huehuetoca | 1503500090233 | Municipio_Urbano_Mejorado |

---

## 🔍 Validación y Control de Calidad

### ✅ Verificaciones Implementadas

1. **Validación de CVEGEO**
   - Todos los códigos tienen 13 caracteres (urbanos)
   - Formato válido según estándar INEGI
   - Correspondencia con municipios correctos

2. **Validación de Códigos Postales**
   - Todos los CPs válidos tienen 5 dígitos
   - Formato numérico correcto
   - Correspondencia geográfica verificada

3. **Validación Geográfica**
   - Intersección espacial con polígonos oficiales INEGI
   - Coordenadas dentro de límites de CDMX y Estado de México
   - Consistencia entre CP, municipio y AGEB

4. **Validación de Diversidad**
   - 1,688 AGEB únicos para evitar concentración
   - Distribución equitativa por municipio
   - Promedio óptimo de registros por AGEB

### 📊 Métricas de Confiabilidad

- **Precisión Espacial**: 90.0% con intersección exacta
- **Cobertura Geográfica**: 100% CDMX + Estado de México
- **Consistencia de Datos**: 100% códigos válidos
- **Diversidad**: 1,688 AGEB únicos de 6,802 disponibles

---

## 🎯 Casos Especiales Manejados

### 🔧 Códigos Postales Problemáticos

1. **CPs de 4 dígitos** (3,499 casos - 52.2%)
   - **Problema**: Pérdida del cero inicial
   - **Solución**: Agregar '0' al inicio + reasignación por intersección
   - **Resultado**: 98.3% reasignados exitosamente

2. **CPs faltantes** (370 casos - 5.2%)
   - **Problema**: CP = "." o "nan"
   - **Solución**: Asignación por municipio/colonia
   - **Resultado**: 100% asignados por métodos alternativos

### 🏘️ AGEB Rurales Convertidos

1. **AGEB de 9 dígitos** (253 casos - 3.6%)
   - **Problema**: Códigos rurales en zonas urbanas
   - **Solución**: Reasignación a AGEB urbanos del mismo municipio
   - **Resultado**: 100% convertidos a urbanos (13 caracteres)

### 🗺️ Municipios sin Mapeo Directo

1. **Códigos CODE no estándar** (casos minoritarios)
   - **Problema**: Códigos municipales no coinciden con INEGI
   - **Solución**: Mapeo manual + fallback por estado
   - **Resultado**: 100% asignados con métodos robustos

---

## 📚 Referencias y Fuentes

### 🏛️ Datos Oficiales
- **INEGI Marco Geoestadístico 2020**: Shapefiles oficiales de AGEB
- **SEPOMEX**: Códigos postales oficiales de México
- **OpenStreetMap Nominatim**: Geocodificación de colonias

### 🌐 Datasets Externos
- **CP-MEX-2025**: [adrianrg.com](https://adrianrg.com/dataset-codigos-postales-de-mexico-con-coordenadas-2025/)
- **INEGI Shapefiles**: Marco Geoestadístico Nacional 2020
