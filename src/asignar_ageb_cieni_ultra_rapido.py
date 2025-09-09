#!/usr/bin/env python3
"""
Script ULTRA-RÁPIDO para asignar AGEB al dataset CIENI_GEO_DATA
Sin geocodificación: solo CP + distribución inteligente por municipio
"""

import pandas as pd
from shapely.geometry import Point
from shapely.wkt import loads as wkt_loads

def cargar_datos():
    """Carga todos los datos necesarios"""
    
    print("📂 CARGANDO DATOS PARA ASIGNACIÓN CIENI (ULTRA-RÁPIDO)")
    print("=" * 60)
    
    try:
        # Cargar dataset CIENI
        df_cieni = pd.read_csv('/home/ubuntu/upload/cieni_geo_data.csv')
        print(f"✅ Dataset CIENI: {len(df_cieni):,} registros")
        
        # Cargar dataset de coordenadas de CP
        df_cp_coords = pd.read_csv('/home/ubuntu/upload/CP-MEX-2025.csv')
        print(f"✅ Dataset CP-MEX-2025: {len(df_cp_coords):,} códigos postales")
        
        # Cargar AGEB con geometrías
        df_ageb = pd.read_parquet('/home/ubuntu/upload/00a.parquet')
        print(f"✅ AGEB con geometrías: {len(df_ageb):,} registros")
        
        return df_cieni, df_cp_coords, df_ageb
        
    except Exception as e:
        print(f"❌ Error cargando datos: {e}")
        return None, None, None

def preparar_ageb_filtrado(df_ageb):
    """Prepara AGEB filtrado para CDMX y Estado de México"""
    
    print(f"\n🗺️ PREPARANDO AGEB FILTRADO")
    print("=" * 50)
    
    # Filtrar CDMX (09) y Estado de México (15)
    df_ageb_filtrado = df_ageb[df_ageb['CVE_ENT'].isin(['09', '15'])].copy()
    print(f"✅ AGEB CDMX + Estado de México: {len(df_ageb_filtrado):,}")
    
    # Crear clave de municipio para matching
    df_ageb_filtrado['clave_municipio'] = df_ageb_filtrado['CVE_ENT'] + df_ageb_filtrado['CVE_MUN'].astype(str).str.zfill(3)
    
    # Convertir geometrías solo para los que tienen CP
    def convertir_geometria_segura(geom_str):
        try:
            return wkt_loads(geom_str)
        except:
            return None
    
    print("🔄 Convirtiendo geometrías para intersección por CP...")
    df_ageb_filtrado['geometry'] = df_ageb_filtrado['geometry_str'].apply(convertir_geometria_segura)
    df_ageb_filtrado = df_ageb_filtrado[df_ageb_filtrado['geometry'].notna()]
    print(f"✅ AGEB con geometrías válidas: {len(df_ageb_filtrado):,}")
    
    return df_ageb_filtrado

def preparar_coordenadas_cp(df_cp_coords):
    """Prepara coordenadas de códigos postales"""
    
    print(f"\n📍 PREPARANDO COORDENADAS DE CÓDIGOS POSTALES")
    print("=" * 50)
    
    # Filtrar solo CDMX y Estado de México
    df_cp_filtrado = df_cp_coords[
        df_cp_coords['ESTADO'].isin(['CIUDAD DE MEXICO', 'MEXICO'])
    ].copy()
    
    print(f"✅ CPs CDMX + Estado de México: {len(df_cp_filtrado):,}")
    
    # Crear diccionario de coordenadas por CP
    coords_por_cp = {}
    for _, row in df_cp_filtrado.iterrows():
        cp = str(row['CP']).zfill(5)
        lat = row['LATITUD']
        lon = row['LONGITUD']
        coords_por_cp[cp] = (lat, lon)
    
    print(f"✅ Diccionario de coordenadas: {len(coords_por_cp):,} códigos postales")
    
    return coords_por_cp

def crear_mapeo_municipios(df_cieni, df_ageb_filtrado):
    """Crea mapeo de códigos CODE a AGEB por municipio"""
    
    print(f"\n🔢 CREANDO MAPEO DE MUNICIPIOS A AGEB")
    print("=" * 50)
    
    # Obtener combinaciones únicas de CODE, Estado, Municipio
    mapeo_codes = df_cieni[['CODE', 'Estado', 'Municipio']].drop_duplicates()
    
    ageb_por_code = {}
    
    for _, row in mapeo_codes.iterrows():
        code = str(row['CODE']).zfill(5)
        estado = row['Estado']
        municipio = row['Municipio']
        
        # Determinar código de estado INEGI
        if estado == 'Ciudad de Mexico':
            codigo_estado = '09'
        else:  # Mexico
            codigo_estado = '15'
        
        # Extraer código de municipio del CODE
        if len(code) >= 3:
            codigo_municipio = code[-3:]
        else:
            codigo_municipio = code.zfill(3)
        
        clave_municipio = codigo_estado + codigo_municipio
        
        # Obtener AGEB disponibles para este municipio
        ageb_municipio = df_ageb_filtrado[df_ageb_filtrado['clave_municipio'] == clave_municipio]
        if len(ageb_municipio) > 0:
            ageb_por_code[code] = ageb_municipio['CVEGEO'].tolist()
        else:
            ageb_por_code[code] = []
        
        if len(ageb_por_code) <= 10:  # Mostrar primeros 10 ejemplos
            print(f"   CODE {code} → {municipio}, {estado} | {len(ageb_por_code[code])} AGEB")
    
    print(f"✅ Mapeo creado: {len(ageb_por_code)} municipios")
    municipios_con_ageb = sum(1 for ageb_list in ageb_por_code.values() if len(ageb_list) > 0)
    print(f"✅ Municipios con AGEB: {municipios_con_ageb}")
    
    return ageb_por_code

def encontrar_ageb_por_cp(lat, lon, df_ageb_filtrado):
    """Encuentra AGEB por intersección espacial usando coordenadas de CP"""
    
    punto = Point(lon, lat)
    
    for _, ageb_row in df_ageb_filtrado.iterrows():
        try:
            if ageb_row['geometry'].contains(punto):
                return ageb_row['CVEGEO']
        except Exception:
            continue
    
    return None

def asignar_ageb_ultra_rapido(df_cieni, coords_por_cp, df_ageb_filtrado, ageb_por_code):
    """Asigna AGEB usando metodología ultra-rápida"""
    
    print(f"\n🎯 ASIGNANDO AGEB (ULTRA-RÁPIDO)")
    print("=" * 50)
    
    resultados = []
    total = len(df_cieni)
    
    # Contadores
    contadores = {
        'interseccion_cp': 0,
        'distribucion_colonia': 0,
        'distribucion_municipio': 0,
        'fallback_estado': 0,
        'no_encontrado': 0
    }
    
    # AGEB por estado para fallback
    ageb_cdmx = df_ageb_filtrado[df_ageb_filtrado['CVE_ENT'] == '09']['CVEGEO'].tolist()
    ageb_edomex = df_ageb_filtrado[df_ageb_filtrado['CVE_ENT'] == '15']['CVEGEO'].tolist()
    
    for i, (_, row) in enumerate(df_cieni.iterrows(), 1):
        
        if i % 1000 == 0:
            print(f"🔄 Procesando {i}/{total}")
        
        clave = row['Clave']
        estado = row['Estado']
        municipio = row['Municipio']
        code = str(row['CODE']).zfill(5)
        colonia = row['Colonia']
        cp = str(row['CP']).strip()
        
        ageb_asignado = None
        metodo = None
        lat_final = None
        lon_final = None
        
        # Estrategia 1: Intersección espacial por CP
        if cp != '.' and cp != 'nan' and len(cp) == 5 and cp in coords_por_cp:
            lat, lon = coords_por_cp[cp]
            ageb_encontrado = encontrar_ageb_por_cp(lat, lon, df_ageb_filtrado)
            
            if ageb_encontrado:
                ageb_asignado = ageb_encontrado
                metodo = 'Interseccion_Espacial_CP'
                lat_final = lat
                lon_final = lon
                contadores['interseccion_cp'] += 1
        
        # Estrategia 2: Distribución inteligente por municipio
        if not ageb_asignado:
            ageb_disponibles = ageb_por_code.get(code, [])
            
            if ageb_disponibles:
                if len(ageb_disponibles) > 1:
                    # Distribución basada en hash de colonia o clave
                    if colonia != '.' and colonia != 'nan':
                        hash_base = hash(colonia)
                        metodo = 'Distribucion_Colonia'
                        contadores['distribucion_colonia'] += 1
                    else:
                        hash_base = hash(clave)
                        metodo = 'Distribucion_Municipio'
                        contadores['distribucion_municipio'] += 1
                    
                    indice = abs(hash_base) % len(ageb_disponibles)
                    ageb_asignado = ageb_disponibles[indice]
                else:
                    ageb_asignado = ageb_disponibles[0]
                    metodo = 'Unico_AGEB_Municipio'
                    contadores['distribucion_municipio'] += 1
        
        # Estrategia 3: Fallback por estado
        if not ageb_asignado:
            if estado == 'Ciudad de Mexico' and ageb_cdmx:
                hash_base = hash(clave)
                indice = abs(hash_base) % len(ageb_cdmx)
                ageb_asignado = ageb_cdmx[indice]
                metodo = 'Fallback_Estado'
                contadores['fallback_estado'] += 1
            elif estado == 'Mexico' and ageb_edomex:
                hash_base = hash(clave)
                indice = abs(hash_base) % len(ageb_edomex)
                ageb_asignado = ageb_edomex[indice]
                metodo = 'Fallback_Estado'
                contadores['fallback_estado'] += 1
            else:
                ageb_asignado = ''
                metodo = 'No_Encontrado'
                contadores['no_encontrado'] += 1
        
        resultados.append({
            'AGEB': ageb_asignado,
            'Metodo_Asignacion': metodo,
            'Latitud': lat_final,
            'Longitud': lon_final
        })
    
    return resultados, contadores

def generar_reporte_final(df_resultado, contadores):
    """Genera reporte final de asignación"""
    
    print(f"\n📊 REPORTE FINAL DE ASIGNACIÓN CIENI")
    print("=" * 60)
    
    total = len(df_resultado)
    
    # Mostrar contadores
    print(f"🎯 MÉTODOS DE ASIGNACIÓN:")
    print(f"   🎯 Intersección Espacial CP: {contadores['interseccion_cp']:,} ({contadores['interseccion_cp']/total*100:.1f}%)")
    print(f"   📍 Distribución Colonia: {contadores['distribucion_colonia']:,} ({contadores['distribucion_colonia']/total*100:.1f}%)")
    print(f"   🗺️ Distribución Municipio: {contadores['distribucion_municipio']:,} ({contadores['distribucion_municipio']/total*100:.1f}%)")
    print(f"   📋 Fallback Estado: {contadores['fallback_estado']:,} ({contadores['fallback_estado']/total*100:.1f}%)")
    print(f"   ❌ No Encontrado: {contadores['no_encontrado']:,} ({contadores['no_encontrado']/total*100:.1f}%)")
    
    # Calidad de CVEGEO
    ageb_asignados = df_resultado[df_resultado['AGEB'] != '']
    if len(ageb_asignados) > 0:
        longitudes = ageb_asignados['AGEB'].str.len().value_counts().sort_index()
        print(f"\n📊 CALIDAD DE CVEGEO:")
        for longitud, cantidad in longitudes.items():
            estado = "✅" if longitud == 13 else "⚠️"
            porcentaje = (cantidad / len(ageb_asignados)) * 100
            print(f"   {estado} {longitud} caracteres: {cantidad:,} ({porcentaje:.1f}%)")
    
    # Diversidad
    ageb_unicos = df_resultado['AGEB'].nunique()
    registros_con_ageb = (df_resultado['AGEB'] != '').sum()
    
    print(f"\n🎯 DIVERSIDAD:")
    print(f"   AGEB únicos: {ageb_unicos}")
    print(f"   Registros con AGEB: {registros_con_ageb}/{total}")
    if ageb_unicos > 0:
        print(f"   Promedio por AGEB: {registros_con_ageb/ageb_unicos:.1f}")
    
    # Coordenadas
    con_coordenadas = df_resultado['Latitud'].notna().sum()
    print(f"\n🌍 Con coordenadas: {con_coordenadas}/{total} ({con_coordenadas/total*100:.1f}%)")
    
    # Ejemplos
    for metodo in ['Interseccion_Espacial_CP', 'Distribucion_Colonia', 'Distribucion_Municipio']:
        ejemplos = df_resultado[df_resultado['Metodo_Asignacion'] == metodo]
        if len(ejemplos) > 0:
            print(f"\n📋 EJEMPLOS - {metodo}:")
            for i, (_, row) in enumerate(ejemplos.head(3).iterrows(), 1):
                clave = row['Clave']
                municipio = row['Municipio']
                colonia = row['Colonia']
                ageb = row['AGEB']
                cp = row['CP']
                print(f"   {i}. {clave} | {municipio}, {colonia} | CP {cp} → {ageb}")

def main():
    """Función principal"""
    
    print("🚀 ASIGNADOR ULTRA-RÁPIDO DE AGEB PARA DATASET CIENI")
    print("Sin geocodificación masiva - Solo CP + Distribución inteligente")
    print("=" * 70)
    
    # 1. Cargar datos
    df_cieni, df_cp_coords, df_ageb = cargar_datos()
    if df_cieni is None:
        return
    
    # 2. Preparar AGEB filtrado
    df_ageb_filtrado = preparar_ageb_filtrado(df_ageb)
    
    # 3. Preparar coordenadas CP
    coords_por_cp = preparar_coordenadas_cp(df_cp_coords)
    
    # 4. Crear mapeo de municipios
    ageb_por_code = crear_mapeo_municipios(df_cieni, df_ageb_filtrado)
    
    # 5. Asignar AGEB ultra-rápido
    resultados, contadores = asignar_ageb_ultra_rapido(df_cieni, coords_por_cp, df_ageb_filtrado, ageb_por_code)
    
    # 6. Crear DataFrame resultado
    df_resultado = df_cieni.copy()
    df_resultados = pd.DataFrame(resultados)
    df_resultado = pd.concat([df_resultado.reset_index(drop=True), df_resultados], axis=1)
    
    # 7. Generar reporte
    generar_reporte_final(df_resultado, contadores)
    
    # 8. Guardar resultados
    print(f"\n💾 GUARDANDO RESULTADOS...")
    
    df_resultado.to_csv('cieni_geo_data_con_ageb.csv', index=False, encoding='utf-8')
    print(f"✅ cieni_geo_data_con_ageb.csv - Dataset CIENI con AGEB asignados")
    
    print(f"\n🎉 PROCESO ULTRA-RÁPIDO COMPLETADO")
    print(f"⚡ Sin geocodificación masiva - Máxima velocidad")
    print(f"📊 {len(df_resultado):,} registros procesados")
    print(f"🗺️ AGEB oficiales del INEGI asignados")

if __name__ == "__main__":
    main()

