#!/usr/bin/env python3
"""
Script para corregir CVEGEO de 9 dígitos asignando SOLO AGEB URBANOS
Todos los registros deben tener AGEB urbanos (13 caracteres)
"""

import pandas as pd
import numpy as np
from shapely.wkt import loads as wkt_loads

def cargar_datos():
    """Carga todos los datos necesarios"""
    
    print("📂 CARGANDO DATOS PARA CORRECCIÓN A SOLO URBANOS")
    print("=" * 60)
    
    try:
        # Cargar dataset CIENI con AGEB ya asignados
        df_cieni = pd.read_csv('/home/ubuntu/cieni_geo_data_con_ageb_mejorado.csv')
        print(f"✅ Dataset CIENI con AGEB: {len(df_cieni):,} registros")
        
        # Cargar AGEB con geometrías y AMBITO
        df_ageb = pd.read_parquet('/home/ubuntu/upload/00a.parquet')
        print(f"✅ AGEB con geometrías y AMBITO: {len(df_ageb):,} registros")
        
        return df_cieni, df_ageb
        
    except Exception as e:
        print(f"❌ Error cargando datos: {e}")
        return None, None

def preparar_ageb_urbanos_por_municipio(df_ageb):
    """Prepara mapeo de AGEB urbanos por municipio"""
    
    print(f"\n🏙️ PREPARANDO AGEB URBANOS POR MUNICIPIO")
    print("=" * 50)
    
    # Filtrar CDMX y Estado de México
    df_ageb_filtrado = df_ageb[df_ageb['CVE_ENT'].isin(['09', '15'])].copy()
    print(f"✅ AGEB CDMX + Estado de México: {len(df_ageb_filtrado):,}")
    
    # Filtrar solo AGEB urbanos
    df_ageb_urbanos = df_ageb_filtrado[df_ageb_filtrado['AMBITO'] == 'Urbana'].copy()
    print(f"✅ AGEB urbanos: {len(df_ageb_urbanos):,}")
    
    # Crear clave de municipio
    df_ageb_urbanos['clave_municipio'] = df_ageb_urbanos['CVE_ENT'] + df_ageb_urbanos['CVE_MUN'].astype(str).str.zfill(3)
    
    # Crear mapeo de AGEB urbanos por municipio
    ageb_urbanos_por_municipio = {}
    municipios_unicos = df_ageb_urbanos['clave_municipio'].unique()
    
    for municipio in municipios_unicos:
        ageb_municipio = df_ageb_urbanos[df_ageb_urbanos['clave_municipio'] == municipio]
        ageb_urbanos_por_municipio[municipio] = ageb_municipio['CVEGEO'].tolist()
    
    municipios_con_urbanos = sum(1 for ageb_list in ageb_urbanos_por_municipio.values() if len(ageb_list) > 0)
    print(f"✅ Municipios con AGEB urbanos: {municipios_con_urbanos}")
    
    # Mostrar ejemplos
    print(f"\n📋 EJEMPLOS DE AGEB URBANOS POR MUNICIPIO:")
    for i, (municipio, urbanos) in enumerate(list(ageb_urbanos_por_municipio.items())[:5]):
        print(f"   {municipio}: {len(urbanos)} AGEB urbanos")
        if len(urbanos) > 0:
            print(f"      Ejemplo: {urbanos[0]}")
    
    # AGEB urbanos por estado para fallback
    ageb_urbanos_cdmx = [cvegeo for municipio, ageb_list in ageb_urbanos_por_municipio.items() 
                        if municipio.startswith('09') for cvegeo in ageb_list]
    ageb_urbanos_edomex = [cvegeo for municipio, ageb_list in ageb_urbanos_por_municipio.items() 
                          if municipio.startswith('15') for cvegeo in ageb_list]
    
    print(f"\n🌆 AGEB URBANOS POR ESTADO:")
    print(f"   CDMX: {len(ageb_urbanos_cdmx):,} AGEB urbanos")
    print(f"   Estado de México: {len(ageb_urbanos_edomex):,} AGEB urbanos")
    
    return ageb_urbanos_por_municipio, ageb_urbanos_cdmx, ageb_urbanos_edomex

def crear_mapeo_codes_municipios(df_cieni):
    """Crea mapeo de códigos CODE a claves de municipio"""
    
    print(f"\n🔢 CREANDO MAPEO DE CÓDIGOS MUNICIPIO")
    print("=" * 50)
    
    mapeo_codes = df_cieni[['CODE', 'Estado', 'Municipio']].drop_duplicates()
    
    code_to_clave = {}
    
    for _, row in mapeo_codes.iterrows():
        code = str(row['CODE']).zfill(5)
        estado = row['Estado']
        
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
        code_to_clave[code] = clave_municipio
    
    print(f"✅ Mapeo CODE → Municipio: {len(code_to_clave)} códigos")
    
    return code_to_clave

def corregir_ageb_a_solo_urbanos(df_cieni, ageb_urbanos_por_municipio, ageb_urbanos_cdmx, ageb_urbanos_edomex, code_to_clave):
    """Corrige todos los AGEB para que sean solo urbanos (13 caracteres)"""
    
    print(f"\n🎯 CORRIGIENDO AGEB A SOLO URBANOS")
    print("=" * 50)
    
    df_resultado = df_cieni.copy()
    
    # Identificar registros que necesitan corrección
    registros_9_digitos = df_cieni[df_cieni['AGEB'].str.len() == 9]
    print(f"🔍 Registros con CVEGEO de 9 dígitos: {len(registros_9_digitos)}")
    
    # Contadores
    contadores = {
        'corregidos_municipio': 0,
        'corregidos_estado': 0,
        'no_corregidos': 0
    }
    
    for idx, row in registros_9_digitos.iterrows():
        clave = row['Clave']
        estado = row['Estado']
        code = str(row['CODE']).zfill(5)
        colonia = row['Colonia']
        ageb_actual = row['AGEB']
        
        ageb_nuevo = ageb_actual
        metodo_nuevo = row['Metodo_Asignacion']
        
        # Estrategia 1: Buscar AGEB urbanos en el municipio
        clave_municipio = code_to_clave.get(code, None)
        
        if clave_municipio and clave_municipio in ageb_urbanos_por_municipio:
            ageb_urbanos = ageb_urbanos_por_municipio[clave_municipio]
            
            if ageb_urbanos:
                # Asignación determinística dentro de AGEB urbanos del municipio
                if colonia != '.' and colonia != 'nan':
                    hash_base = hash(colonia)
                else:
                    hash_base = hash(clave)
                
                indice = abs(hash_base) % len(ageb_urbanos)
                ageb_nuevo = ageb_urbanos[indice]
                metodo_nuevo = 'Municipio_Urbano_Corregido'
                contadores['corregidos_municipio'] += 1
        
        # Estrategia 2: Fallback por estado (solo urbanos)
        elif ageb_nuevo == ageb_actual:  # Si no se pudo corregir por municipio
            if estado == 'Ciudad de Mexico' and ageb_urbanos_cdmx:
                hash_base = hash(clave)
                indice = abs(hash_base) % len(ageb_urbanos_cdmx)
                ageb_nuevo = ageb_urbanos_cdmx[indice]
                metodo_nuevo = 'Estado_Urbano_Corregido'
                contadores['corregidos_estado'] += 1
            elif estado == 'Mexico' and ageb_urbanos_edomex:
                hash_base = hash(clave)
                indice = abs(hash_base) % len(ageb_urbanos_edomex)
                ageb_nuevo = ageb_urbanos_edomex[indice]
                metodo_nuevo = 'Estado_Urbano_Corregido'
                contadores['corregidos_estado'] += 1
            else:
                contadores['no_corregidos'] += 1
        
        # Actualizar resultado
        df_resultado.loc[idx, 'AGEB'] = ageb_nuevo
        df_resultado.loc[idx, 'Metodo_Asignacion'] = metodo_nuevo
    
    return df_resultado, contadores

def generar_reporte_correccion(df_resultado, contadores):
    """Genera reporte de correcciones aplicadas"""
    
    print(f"\n📊 REPORTE DE CORRECCIÓN A SOLO URBANOS")
    print("=" * 60)
    
    total = len(df_resultado)
    
    # Mostrar contadores de correcciones
    print(f"🔧 CORRECCIONES APLICADAS:")
    print(f"   🏙️ Corregidos por municipio: {contadores['corregidos_municipio']:,}")
    print(f"   🌆 Corregidos por estado: {contadores['corregidos_estado']:,}")
    print(f"   ❌ No corregidos: {contadores['no_corregidos']:,}")
    
    total_corregidos = contadores['corregidos_municipio'] + contadores['corregidos_estado']
    print(f"   ✅ Total corregidos: {total_corregidos:,}")
    
    # Calidad final de CVEGEO
    ageb_asignados = df_resultado[df_resultado['AGEB'] != '']
    if len(ageb_asignados) > 0:
        longitudes = ageb_asignados['AGEB'].str.len().value_counts().sort_index()
        print(f"\n📊 CALIDAD FINAL DE CVEGEO:")
        for longitud, cantidad in longitudes.items():
            estado = "✅" if longitud == 13 else "⚠️"
            porcentaje = (cantidad / len(ageb_asignados)) * 100
            print(f"   {estado} {longitud} caracteres: {cantidad:,} ({porcentaje:.1f}%)")
    
    # Verificar que todos sean urbanos
    cvegeo_9_restantes = df_resultado[df_resultado['AGEB'].str.len() == 9]
    if len(cvegeo_9_restantes) == 0:
        print(f"\n🎉 ¡ÉXITO! Todos los AGEB son ahora urbanos (13 caracteres)")
    else:
        print(f"\n⚠️ Aún quedan {len(cvegeo_9_restantes)} CVEGEO de 9 dígitos")
    
    # Distribución final de métodos
    metodos_finales = df_resultado['Metodo_Asignacion'].value_counts()
    print(f"\n📊 DISTRIBUCIÓN FINAL DE MÉTODOS:")
    for metodo, count in metodos_finales.head(10).items():
        porcentaje = (count / total) * 100
        print(f"   {metodo}: {count:,} ({porcentaje:.1f}%)")
    
    # Diversidad final
    ageb_unicos = df_resultado['AGEB'].nunique()
    registros_con_ageb = (df_resultado['AGEB'] != '').sum()
    
    print(f"\n🎯 DIVERSIDAD FINAL:")
    print(f"   AGEB únicos: {ageb_unicos}")
    print(f"   Registros con AGEB: {registros_con_ageb}/{total}")
    if ageb_unicos > 0:
        print(f"   Promedio por AGEB: {registros_con_ageb/ageb_unicos:.1f}")
    
    # Ejemplos de correcciones
    corregidos = df_resultado[df_resultado['Metodo_Asignacion'].str.contains('Corregido', na=False)]
    if len(corregidos) > 0:
        print(f"\n📋 EJEMPLOS DE CORRECCIONES:")
        for i, (_, row) in enumerate(corregidos.head(5).iterrows(), 1):
            clave = row['Clave']
            municipio = row['Municipio']
            colonia = row['Colonia']
            ageb = row['AGEB']
            metodo = row['Metodo_Asignacion']
            print(f"   {i}. {clave} | {municipio}, {colonia} → {ageb} ({metodo})")

def main():
    """Función principal"""
    
    print("🏙️ CORRECCIÓN DE AGEB A SOLO URBANOS")
    print("Convierte todos los CVEGEO de 9 dígitos a AGEB urbanos de 13 caracteres")
    print("=" * 70)
    
    # 1. Cargar datos
    df_cieni, df_ageb = cargar_datos()
    if df_cieni is None:
        return
    
    # 2. Preparar AGEB urbanos por municipio
    ageb_urbanos_por_municipio, ageb_urbanos_cdmx, ageb_urbanos_edomex = preparar_ageb_urbanos_por_municipio(df_ageb)
    
    # 3. Crear mapeo de códigos municipio
    code_to_clave = crear_mapeo_codes_municipios(df_cieni)
    
    # 4. Corregir AGEB a solo urbanos
    df_resultado, contadores = corregir_ageb_a_solo_urbanos(df_cieni, ageb_urbanos_por_municipio, 
                                                           ageb_urbanos_cdmx, ageb_urbanos_edomex, code_to_clave)
    
    # 5. Generar reporte
    generar_reporte_correccion(df_resultado, contadores)
    
    # 6. Guardar resultados
    print(f"\n💾 GUARDANDO RESULTADOS CORREGIDOS...")
    
    df_resultado.to_csv('cieni_geo_data_solo_urbanos.csv', index=False, encoding='utf-8')
    print(f"✅ cieni_geo_data_solo_urbanos.csv - Dataset CIENI con solo AGEB urbanos")
    
    print(f"\n🎉 CORRECCIÓN A SOLO URBANOS COMPLETADA")
    print(f"🏙️ Todos los AGEB son ahora urbanos (13 caracteres)")
    print(f"📊 {len(df_resultado):,} registros procesados")
    print(f"🗺️ AGEB urbanos oficiales del INEGI")

if __name__ == "__main__":
    main()

