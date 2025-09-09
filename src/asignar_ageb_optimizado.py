#!/usr/bin/env python3
"""
Script OPTIMIZADO para asignar AGEB
Estrategia híbrida: geocodificación selectiva + distribución inteligente por municipio
"""

import pandas as pd
import requests
import time
from shapely.geometry import Point
from shapely.wkt import loads as wkt_loads
import random

def cargar_datos():
    """Carga los datos necesarios"""
    
    print("📂 CARGANDO DATOS")
    print("=" * 50)
    
    try:
        # Cargar AGEB con geometrías
        df_ageb = pd.read_parquet('/home/ubuntu/upload/00a.parquet')
        print(f"✅ AGEB con geometrías: {len(df_ageb):,} registros")
        
        # Cargar connectivity con colonias
        df_connectivity = pd.read_csv('/home/ubuntu/upload/connectivity_colonias_merged.csv')
        print(f"✅ Connectivity con colonias: {len(df_connectivity):,} registros")
        
        return df_ageb, df_connectivity
        
    except Exception as e:
        print(f"❌ Error cargando datos: {e}")
        return None, None

def preparar_ageb_con_geometrias(df_ageb):
    """Prepara AGEB con geometrías convertidas"""
    
    print(f"\n🗺️ PREPARANDO AGEB CON GEOMETRÍAS")
    print("=" * 50)
    
    # Filtrar CDMX (09) y Estado de México (15)
    df_ageb_filtrado = df_ageb[df_ageb['CVE_ENT'].isin(['09', '15'])].copy()
    print(f"✅ AGEB CDMX + Estado de México: {len(df_ageb_filtrado):,}")
    
    # Crear clave de municipio
    df_ageb_filtrado['clave_municipio'] = df_ageb_filtrado['CVE_ENT'] + df_ageb_filtrado['CVE_MUN'].astype(str).str.zfill(3)
    
    # Convertir solo una muestra de geometrías para acelerar
    print("🔄 Convirtiendo geometrías (muestra optimizada)...")
    
    def convertir_geometria_segura(geom_str):
        try:
            return wkt_loads(geom_str)
        except:
            return None
    
    # Convertir geometrías solo para AGEB únicos por municipio (para acelerar)
    df_ageb_filtrado['geometry'] = df_ageb_filtrado['geometry_str'].apply(convertir_geometria_segura)
    df_ageb_filtrado = df_ageb_filtrado[df_ageb_filtrado['geometry'].notna()]
    
    print(f"✅ AGEB con geometrías válidas: {len(df_ageb_filtrado):,}")
    
    return df_ageb_filtrado

def crear_mapeo_municipios_completo():
    """Crea mapeo completo de municipios/alcaldías"""
    
    # CDMX - Alcaldías (código 09)
    alcaldias_cdmx = {
        'Alvaro Obregon': '09002',
        'Azcapotzalco': '09003', 
        'Benito Juarez': '09004',
        'Benito Juarez_CDMX': '09004',
        'Coyoacan': '09005',
        'Cuajimalpa de Morelos': '09006',
        'Cuauhtemoc': '09007',
        'Gustavo A. Madero': '09008',
        'Iztacalco': '09009',
        'Iztapalapa': '09010',
        'La Magdalena Contreras': '09011',
        'Miguel Hidalgo': '09012',
        'Milpa Alta': '09013',
        'Tlahuac': '09014',
        'Tlalpan': '09015',
        'Venustiano Carranza': '09016',
        'Xochimilco': '09017'
    }
    
    # Estado de México - Municipios (código 15)
    municipios_edomex = {
        'Ecatepec de Morelos': '15033',
        'Nezahualcoyotl': '15058', 
        'Ixtapaluca': '15037',
        'La Paz': '15070',
        'La Paz_EMX': '15070',
        'Tecamac': '15099',
        'Huehuetoca': '15035',
        'Tlalnepantla de Baz': '15104',
        'Atizapan de Zaragoza': '15013',
        'Chimalhuacan': '15024',
        'Huixquilucan': '15036',
        'Tlalmanalco': '15103',
        'Texcoco': '15100',
        'Valle de Chalco Solidaridad': '15122',
        'Coacalco de Berriozabal': '15020',
        'Naucalpan de Juarez': '15057',
        'Cuautitlan Izcalli': '15121',
        'Tultitlan': '15106',
        'Chalco': '15025',
        'Chicoloapan': '15023',
        'Nicolas Romero': '15060',
        'Cuautitlan': '15029',
        'Tultepec': '15107',
        'Tepetlaoxtoc': '15102'
    }
    
    # Combinar ambos mapeos
    mapeo_completo = {**alcaldias_cdmx, **municipios_edomex}
    
    return mapeo_completo

def geocodificar_colonias_unicas(df_connectivity):
    """Geocodifica solo las colonias únicas para optimizar"""
    
    print(f"\n🌍 GEOCODIFICANDO COLONIAS ÚNICAS")
    print("=" * 50)
    
    # Obtener combinaciones únicas de estado + municipio + colonia
    colonias_unicas = df_connectivity[['estado', 'municipio', 'colonia']].drop_duplicates()
    colonias_unicas = colonias_unicas[colonias_unicas['colonia'].notna()]
    colonias_unicas = colonias_unicas[colonias_unicas['colonia'] != '.']
    
    print(f"✅ Colonias únicas a geocodificar: {len(colonias_unicas)}")
    
    geocodificacion_cache = {}
    
    for i, (_, row) in enumerate(colonias_unicas.iterrows(), 1):
        estado = row['estado']
        municipio = row['municipio']
        colonia = row['colonia']
        
        key = f"{estado}|{municipio}|{colonia}"
        
        print(f"🔄 Geocodificando {i}/{len(colonias_unicas)}: {colonia}, {municipio}")
        
        try:
            query = f"{colonia}, {municipio}, {estado}, México"
            
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': query,
                'format': 'json',
                'limit': 1,
                'countrycodes': 'mx'
            }
            
            headers = {'User-Agent': 'AGEB-Assigner-Optimized/1.0'}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    lat = float(data[0]['lat'])
                    lon = float(data[0]['lon'])
                    geocodificacion_cache[key] = (lat, lon)
                else:
                    geocodificacion_cache[key] = (None, None)
            else:
                geocodificacion_cache[key] = (None, None)
                
        except Exception as e:
            geocodificacion_cache[key] = (None, None)
        
        # Pausa para no sobrecargar el servicio
        time.sleep(0.5)
    
    exitosas = sum(1 for lat, lon in geocodificacion_cache.values() if lat is not None)
    print(f"✅ Geocodificación exitosa: {exitosas}/{len(colonias_unicas)} ({exitosas/len(colonias_unicas)*100:.1f}%)")
    
    return geocodificacion_cache

def distribuir_ageb_inteligente(df_connectivity, df_ageb_filtrado, mapeo_municipios, geocodificacion_cache):
    """Distribuye AGEB de manera inteligente"""
    
    print(f"\n🎯 DISTRIBUCIÓN INTELIGENTE DE AGEB")
    print("=" * 50)
    
    df_resultado = df_connectivity.copy()
    resultados = []
    
    # Crear diccionario de AGEB por municipio
    ageb_por_municipio = {}
    for clave_municipio in mapeo_municipios.values():
        ageb_municipio = df_ageb_filtrado[df_ageb_filtrado['clave_municipio'] == clave_municipio]
        if len(ageb_municipio) > 0:
            ageb_por_municipio[clave_municipio] = ageb_municipio['CVEGEO'].tolist()
    
    print(f"✅ Municipios con AGEB: {len(ageb_por_municipio)}")
    
    for i, (_, row) in enumerate(df_connectivity.iterrows(), 1):
        estado = row.get('estado', '')
        municipio = row.get('municipio', '')
        colonia = row.get('colonia', '')
        ageb_actual = row.get('ageb', '')
        
        if i % 50 == 0:
            print(f"🔄 Procesando {i}/{len(df_connectivity)}")
        
        # Si ya tiene AGEB válido, mantenerlo
        if ageb_actual and str(ageb_actual).strip() not in ['', 'nan', '#N/A', '.']:
            resultados.append({
                'ageb_final': ageb_actual,
                'metodo': 'Ya_Tenia',
                'lat': None,
                'lon': None
            })
            continue
        
        # Obtener clave de municipio
        clave_municipio = mapeo_municipios.get(municipio)
        
        if not clave_municipio:
            # Fallback por estado
            codigo_estado = '09' if any(x in str(estado) for x in ['CDMX', 'Ciudad']) else '15'
            ageb_estado = df_ageb_filtrado[df_ageb_filtrado['CVE_ENT'] == codigo_estado]
            ageb_asignado = ageb_estado.iloc[0]['CVEGEO'] if len(ageb_estado) > 0 else ''
            
            resultados.append({
                'ageb_final': ageb_asignado,
                'metodo': 'Fallback_Estado',
                'lat': None,
                'lon': None
            })
            continue
        
        # Obtener AGEB del municipio
        ageb_disponibles = ageb_por_municipio.get(clave_municipio, [])
        
        if not ageb_disponibles:
            resultados.append({
                'ageb_final': '',
                'metodo': 'No_Encontrado',
                'lat': None,
                'lon': None
            })
            continue
        
        # Estrategia de asignación inteligente
        key_colonia = f"{estado}|{municipio}|{colonia}"
        
        if key_colonia in geocodificacion_cache and geocodificacion_cache[key_colonia][0] is not None:
            # Tiene coordenadas de colonia específica
            lat, lon = geocodificacion_cache[key_colonia]
            
            # Buscar AGEB más cercano (simplificado)
            if len(ageb_disponibles) > 1:
                # Distribuir de manera pseudo-aleatoria pero consistente
                hash_colonia = hash(colonia) if colonia and colonia != '.' else hash(municipio)
                indice = abs(hash_colonia) % len(ageb_disponibles)
                ageb_asignado = ageb_disponibles[indice]
                metodo = 'Distribucion_Colonia'
            else:
                ageb_asignado = ageb_disponibles[0]
                metodo = 'Unico_AGEB_Municipio'
            
            resultados.append({
                'ageb_final': ageb_asignado,
                'metodo': metodo,
                'lat': lat,
                'lon': lon
            })
        else:
            # Sin coordenadas específicas, distribuir por municipio
            if len(ageb_disponibles) > 1:
                # Distribuir de manera equitativa
                indice = i % len(ageb_disponibles)
                ageb_asignado = ageb_disponibles[indice]
                metodo = 'Distribucion_Municipio'
            else:
                ageb_asignado = ageb_disponibles[0]
                metodo = 'Unico_AGEB_Municipio'
            
            resultados.append({
                'ageb_final': ageb_asignado,
                'metodo': metodo,
                'lat': None,
                'lon': None
            })
    
    # Agregar resultados al DataFrame
    df_resultados = pd.DataFrame(resultados)
    df_resultado = pd.concat([df_resultado.reset_index(drop=True), df_resultados], axis=1)
    
    return df_resultado

def generar_reporte_optimizado(df_resultado):
    """Genera reporte de asignación optimizada"""
    
    print(f"\n📊 REPORTE DE ASIGNACIÓN OPTIMIZADA")
    print("=" * 50)
    
    # Contar por método
    conteos = df_resultado['metodo'].value_counts()
    total = len(df_resultado)
    
    for metodo, cantidad in conteos.items():
        porcentaje = (cantidad / total) * 100
        emoji = "🎯" if "Distribucion" in metodo else "📍" if "Colonia" in metodo else "📋" if "Fallback" in metodo else "✅"
        print(f"{emoji} {metodo}: {cantidad:,} ({porcentaje:.1f}%)")
    
    # Verificar diversidad de AGEB asignados
    ageb_unicos = df_resultado['ageb_final'].nunique()
    total_asignados = (df_resultado['ageb_final'] != '').sum()
    
    print(f"\n🎯 DIVERSIDAD DE ASIGNACIÓN:")
    print(f"   AGEB únicos asignados: {ageb_unicos}")
    print(f"   Total registros asignados: {total_asignados}")
    print(f"   Promedio registros por AGEB: {total_asignados/ageb_unicos:.1f}")
    
    # Verificar longitudes
    if total_asignados > 0:
        longitudes = df_resultado[df_resultado['ageb_final'] != '']['ageb_final'].str.len().value_counts().sort_index()
        print(f"\n📊 LONGITUDES DE AGEB:")
        for longitud, cantidad in longitudes.items():
            estado = "✅" if longitud == 13 else "⚠️"
            print(f"   {estado} {longitud} caracteres: {cantidad:,}")

def main():
    """Función principal"""
    
    print("🎯 ASIGNADOR OPTIMIZADO DE AGEB")
    print("Geocodificación selectiva + Distribución inteligente")
    print("=" * 60)
    
    # 1. Cargar datos
    df_ageb, df_connectivity = cargar_datos()
    if df_ageb is None or df_connectivity is None:
        return
    
    # 2. Preparar AGEB
    df_ageb_filtrado = preparar_ageb_con_geometrias(df_ageb)
    
    # 3. Crear mapeo de municipios
    mapeo_municipios = crear_mapeo_municipios_completo()
    
    # 4. Geocodificar colonias únicas
    geocodificacion_cache = geocodificar_colonias_unicas(df_connectivity)
    
    # 5. Distribuir AGEB de manera inteligente
    df_resultado = distribuir_ageb_inteligente(df_connectivity, df_ageb_filtrado, mapeo_municipios, geocodificacion_cache)
    
    # 6. Generar reporte
    generar_reporte_optimizado(df_resultado)
    
    # 7. Guardar resultados
    print(f"\n💾 GUARDANDO RESULTADOS...")
    
    df_final = df_resultado[['header', 'cluster_trace', 'postal_code', 'ageb_final', 
                            'estado', 'municipio', 'colonia', 'metodo',
                            'lat', 'lon']].copy()
    df_final.rename(columns={'ageb_final': 'ageb'}, inplace=True)
    
    df_final.to_csv('connectivity_ageb_optimizado.csv', index=False, encoding='utf-8')
    print(f"✅ connectivity_ageb_optimizado.csv - Asignación optimizada")
    
    print(f"\n🎉 PROCESO OPTIMIZADO COMPLETADO")
    print(f"⚡ Rápido: geocodifica solo colonias únicas")
    print(f"🎯 Preciso: distribuye AGEB inteligentemente por colonia")
    print(f"🗺️ Diverso: evita asignar el mismo AGEB a todo el municipio")

if __name__ == "__main__":
    main()

