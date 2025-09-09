#!/usr/bin/env python3
"""
Script para corregir códigos postales de 4 dígitos agregando 0 inicial
y reasignar AGEB usando las coordenadas correctas
"""

import pandas as pd
import numpy as np
from shapely.geometry import Point
from shapely.wkt import loads as wkt_loads

def cargar_datos():
    """Carga todos los datos necesarios"""
    
    print("📂 CARGANDO DATOS PARA CORRECCIÓN DE CPs DE 4 DÍGITOS")
    print("=" * 60)
    
    try:
        # Cargar dataset CIENI
        df_cieni = pd.read_csv('/home/ubuntu/cieni_geo_data_solo_urbanos.csv')
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

def analizar_cps_4_digitos(df_cieni):
    """Analiza códigos postales de 4 dígitos"""
    
    print(f"\n🔍 ANALIZANDO CÓDIGOS POSTALES DE 4 DÍGITOS")
    print("=" * 50)
    
    # Filtrar CPs válidos
    cps_validos = df_cieni[~df_cieni['CP'].isin(['.', 'nan']) & df_cieni['CP'].notna()].copy()
    print(f"✅ CPs válidos: {len(cps_validos):,} registros")
    
    # Convertir a string y analizar longitudes
    cps_validos['CP_str'] = cps_validos['CP'].astype(str)
    longitudes_cp = cps_validos['CP_str'].str.len().value_counts().sort_index()
    
    print(f"\n📊 DISTRIBUCIÓN POR LONGITUD:")
    for longitud, cantidad in longitudes_cp.items():
        porcentaje = (cantidad / len(cps_validos)) * 100
        estado = "⚠️" if longitud == 4 else "✅" if longitud == 5 else "❓"
        print(f"   {estado} {longitud} dígitos: {cantidad:,} ({porcentaje:.1f}%)")
    
    # Identificar CPs de 4 dígitos
    cps_4_digitos = cps_validos[cps_validos['CP_str'].str.len() == 4]
    print(f"\n⚠️ CPs de 4 dígitos a corregir: {len(cps_4_digitos):,}")
    
    return cps_4_digitos

def preparar_coordenadas_cp(df_cp_coords):
    """Prepara coordenadas de códigos postales"""
    
    print(f"\n📍 PREPARANDO COORDENADAS DE CÓDIGOS POSTALES")
    print("=" * 50)
    
    # Filtrar solo CDMX y Estado de México
    df_cp_filtrado = df_cp_coords[
        df_cp_coords['ESTADO'].isin(['CIUDAD DE MEXICO', 'MEXICO'])
    ].copy()
    
    print(f"✅ CPs CDMX + Estado de México: {len(df_cp_filtrado):,}")
    
    # Crear diccionario de coordenadas por CP (asegurar 5 dígitos)
    coords_por_cp = {}
    for _, row in df_cp_filtrado.iterrows():
        cp = str(row['CP']).zfill(5)  # Asegurar 5 dígitos
        lat = row['LATITUD']
        lon = row['LONGITUD']
        coords_por_cp[cp] = (lat, lon)
    
    print(f"✅ Diccionario de coordenadas: {len(coords_por_cp):,} códigos postales")
    
    return coords_por_cp

def preparar_ageb_urbanos(df_ageb):
    """Prepara AGEB urbanos para intersección espacial"""
    
    print(f"\n🏙️ PREPARANDO AGEB URBANOS PARA INTERSECCIÓN")
    print("=" * 50)
    
    # Filtrar CDMX y Estado de México, solo urbanos
    df_ageb_urbanos = df_ageb[
        (df_ageb['CVE_ENT'].isin(['09', '15'])) & 
        (df_ageb['AMBITO'] == 'Urbana')
    ].copy()
    
    print(f"✅ AGEB urbanos CDMX + Estado de México: {len(df_ageb_urbanos):,}")
    
    # Convertir geometrías
    def convertir_geometria_segura(geom_str):
        try:
            return wkt_loads(geom_str)
        except:
            return None
    
    print("🔄 Convirtiendo geometrías...")
    df_ageb_urbanos['geometry'] = df_ageb_urbanos['geometry_str'].apply(convertir_geometria_segura)
    df_ageb_urbanos = df_ageb_urbanos[df_ageb_urbanos['geometry'].notna()]
    print(f"✅ AGEB urbanos con geometrías válidas: {len(df_ageb_urbanos):,}")
    
    return df_ageb_urbanos

def encontrar_ageb_por_interseccion(lat, lon, df_ageb_urbanos):
    """Encuentra AGEB urbano por intersección espacial"""
    
    punto = Point(lon, lat)  # Shapely usa (x, y) = (lon, lat)
    
    for _, ageb_row in df_ageb_urbanos.iterrows():
        try:
            if ageb_row['geometry'].contains(punto):
                return ageb_row['CVEGEO']
        except Exception:
            continue
    
    return None

def corregir_cps_y_reasignar_ageb(df_cieni, coords_por_cp, df_ageb_urbanos):
    """Corrige CPs de 4 dígitos y reasigna AGEB"""
    
    print(f"\n🎯 CORRIGIENDO CPs DE 4 DÍGITOS Y REASIGNANDO AGEB")
    print("=" * 60)
    
    df_resultado = df_cieni.copy()
    
    # Contadores
    contadores = {
        'cps_corregidos': 0,
        'ageb_mejorados_interseccion': 0,
        'ageb_sin_mejora': 0,
        'cps_sin_coordenadas': 0
    }
    
    total = len(df_cieni)
    
    for i, (idx, row) in enumerate(df_cieni.iterrows(), 1):
        
        if i % 1000 == 0:
            print(f"🔄 Procesando {i}/{total}")
        
        clave = row['Clave']
        cp_original = str(row['CP']).strip()
        ageb_actual = row['AGEB']
        metodo_actual = row['Metodo_Asignacion']
        lat_actual = row.get('Latitud', None)
        lon_actual = row.get('Longitud', None)
        
        # Variables para resultado
        cp_nuevo = cp_original
        ageb_nuevo = ageb_actual
        metodo_nuevo = metodo_actual
        lat_nueva = lat_actual
        lon_nueva = lon_actual
        
        # Corregir CP de 4 dígitos
        if cp_original != '.' and cp_original != 'nan' and len(cp_original) == 4:
            cp_nuevo = '0' + cp_original  # Agregar 0 inicial
            contadores['cps_corregidos'] += 1
            
            # Intentar reasignar AGEB con coordenadas correctas
            if cp_nuevo in coords_por_cp:
                lat, lon = coords_por_cp[cp_nuevo]
                ageb_encontrado = encontrar_ageb_por_interseccion(lat, lon, df_ageb_urbanos)
                
                if ageb_encontrado:
                    ageb_nuevo = ageb_encontrado
                    metodo_nuevo = 'Interseccion_Espacial_CP_Corregido'
                    lat_nueva = lat
                    lon_nueva = lon
                    contadores['ageb_mejorados_interseccion'] += 1
                else:
                    contadores['ageb_sin_mejora'] += 1
            else:
                contadores['cps_sin_coordenadas'] += 1
        
        # Actualizar resultado
        df_resultado.loc[idx, 'CP'] = cp_nuevo
        df_resultado.loc[idx, 'AGEB'] = ageb_nuevo
        df_resultado.loc[idx, 'Metodo_Asignacion'] = metodo_nuevo
        df_resultado.loc[idx, 'Latitud'] = lat_nueva
        df_resultado.loc[idx, 'Longitud'] = lon_nueva
    
    return df_resultado, contadores

def generar_reporte_correccion_cp(df_resultado, contadores):
    """Genera reporte de correcciones de CP y AGEB"""
    
    print(f"\n📊 REPORTE DE CORRECCIÓN DE CPs Y REASIGNACIÓN AGEB")
    print("=" * 70)
    
    total = len(df_resultado)
    
    # Mostrar contadores
    print(f"🔧 CORRECCIONES DE CÓDIGOS POSTALES:")
    print(f"   📮 CPs de 4 dígitos corregidos: {contadores['cps_corregidos']:,}")
    print(f"   🎯 AGEB mejorados por intersección: {contadores['ageb_mejorados_interseccion']:,}")
    print(f"   ⚠️ AGEB sin mejora: {contadores['ageb_sin_mejora']:,}")
    print(f"   ❌ CPs sin coordenadas: {contadores['cps_sin_coordenadas']:,}")
    
    # Verificar calidad final de CPs
    cps_validos = df_resultado[~df_resultado['CP'].isin(['.', 'nan']) & df_resultado['CP'].notna()]
    if len(cps_validos) > 0:
        cps_str = cps_validos['CP'].astype(str)
        longitudes_cp = cps_str.str.len().value_counts().sort_index()
        
        print(f"\n📊 CALIDAD FINAL DE CÓDIGOS POSTALES:")
        for longitud, cantidad in longitudes_cp.items():
            estado = "✅" if longitud == 5 else "⚠️"
            porcentaje = (cantidad / len(cps_validos)) * 100
            print(f"   {estado} {longitud} dígitos: {cantidad:,} ({porcentaje:.1f}%)")
    
    # Verificar calidad de AGEB
    ageb_asignados = df_resultado[df_resultado['AGEB'] != '']
    if len(ageb_asignados) > 0:
        longitudes_ageb = ageb_asignados['AGEB'].str.len().value_counts().sort_index()
        print(f"\n📊 CALIDAD FINAL DE AGEB:")
        for longitud, cantidad in longitudes_ageb.items():
            estado = "✅" if longitud == 13 else "⚠️"
            porcentaje = (cantidad / len(ageb_asignados)) * 100
            print(f"   {estado} {longitud} caracteres: {cantidad:,} ({porcentaje:.1f}%)")
    
    # Distribución de métodos
    metodos_finales = df_resultado['Metodo_Asignacion'].value_counts()
    print(f"\n📊 DISTRIBUCIÓN FINAL DE MÉTODOS:")
    for metodo, count in metodos_finales.head(10).items():
        porcentaje = (count / total) * 100
        print(f"   {metodo}: {count:,} ({porcentaje:.1f}%)")
    
    # Coordenadas finales
    con_coordenadas = df_resultado['Latitud'].notna().sum()
    print(f"\n🌍 Registros con coordenadas: {con_coordenadas}/{total} ({con_coordenadas/total*100:.1f}%)")
    
    # Ejemplos de correcciones
    corregidos = df_resultado[df_resultado['Metodo_Asignacion'] == 'Interseccion_Espacial_CP_Corregido']
    if len(corregidos) > 0:
        print(f"\n📋 EJEMPLOS DE CPs CORREGIDOS CON AGEB MEJORADO:")
        for i, (_, row) in enumerate(corregidos.head(5).iterrows(), 1):
            clave = row['Clave']
            municipio = row['Municipio']
            colonia = row['Colonia']
            cp = row['CP']
            ageb = row['AGEB']
            print(f"   {i}. {clave} | {municipio}, {colonia} | CP: {cp} → AGEB: {ageb}")

def main():
    """Función principal"""
    
    print("📮 CORRECCIÓN DE CÓDIGOS POSTALES DE 4 DÍGITOS")
    print("Agrega 0 inicial y reasigna AGEB con coordenadas correctas")
    print("=" * 70)
    
    # 1. Cargar datos
    df_cieni, df_cp_coords, df_ageb = cargar_datos()
    if df_cieni is None:
        return
    
    # 2. Analizar CPs de 4 dígitos
    cps_4_digitos = analizar_cps_4_digitos(df_cieni)
    
    # 3. Preparar coordenadas CP
    coords_por_cp = preparar_coordenadas_cp(df_cp_coords)
    
    # 4. Preparar AGEB urbanos
    df_ageb_urbanos = preparar_ageb_urbanos(df_ageb)
    
    # 5. Corregir CPs y reasignar AGEB
    df_resultado, contadores = corregir_cps_y_reasignar_ageb(df_cieni, coords_por_cp, df_ageb_urbanos)
    
    # 6. Generar reporte
    generar_reporte_correccion_cp(df_resultado, contadores)
    
    # 7. Guardar resultados
    print(f"\n💾 GUARDANDO RESULTADOS CORREGIDOS...")
    
    df_resultado.to_csv('cieni_geo_data_cp_corregidos.csv', index=False, encoding='utf-8')
    print(f"✅ cieni_geo_data_cp_corregidos.csv - Dataset CIENI con CPs corregidos")
    
    print(f"\n🎉 CORRECCIÓN DE CPs DE 4 DÍGITOS COMPLETADA")
    print(f"📮 Códigos postales normalizados a 5 dígitos")
    print(f"🎯 AGEB reasignados con coordenadas exactas")
    print(f"📊 {len(df_resultado):,} registros procesados")

if __name__ == "__main__":
    main()

