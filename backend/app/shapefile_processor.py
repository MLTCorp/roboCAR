"""
Shapefile Processor - Extrai e converte Shapefiles para GeoJSON
Processa o ZIP do CAR e extrai arquivos .shp de subpastas, convertendo para GeoJSON
"""
import zipfile
import os
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def processar_shapefile_car(zip_path: str) -> Dict[str, dict]:
    """
    Processa o ZIP do CAR e extrai todos os shapefiles, convertendo para GeoJSON

    Args:
        zip_path: Caminho para o arquivo .zip baixado do CAR

    Returns:
        Dict com camadas GeoJSON organizadas por nome da pasta
        Exemplo: {
            "area_imovel": {...GeoJSON...},
            "cobertura_solo": {...GeoJSON...},
            ...
        }
    """
    logger.info(f"Iniciando processamento do shapefile: {zip_path}")

    if not os.path.exists(zip_path):
        raise FileNotFoundError(f"Arquivo ZIP não encontrado: {zip_path}")

    geojson_layers = {}
    temp_dir = None

    try:
        # Criar diretório temporário para extração
        temp_dir = tempfile.mkdtemp(prefix="car_shapefile_")
        logger.info(f"Diretório temporário criado: {temp_dir}")

        # Extrair ZIP principal
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            logger.info(f"ZIP principal extraído com {len(zip_ref.namelist())} arquivos")

        # Buscar todos os arquivos ZIP dentro do diretório extraído
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.lower().endswith('.zip'):
                    subzip_path = os.path.join(root, file)
                    logger.info(f"Encontrado sub-ZIP: {file}")

                    # Extrair sub-ZIP
                    subdir = os.path.join(root, file.replace('.zip', ''))
                    os.makedirs(subdir, exist_ok=True)

                    try:
                        with zipfile.ZipFile(subzip_path, 'r') as subzip_ref:
                            subzip_ref.extractall(subdir)
                            logger.info(f"Sub-ZIP extraído: {file}")
                    except Exception as e:
                        logger.warning(f"Erro ao extrair sub-ZIP {file}: {e}")
                        continue

        # Buscar todos os arquivos .shp
        shp_files = []
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.lower().endswith('.shp'):
                    shp_path = os.path.join(root, file)
                    shp_files.append(shp_path)
                    logger.info(f"Shapefile encontrado: {file}")

        logger.info(f"Total de {len(shp_files)} shapefiles encontrados")

        # Processar cada shapefile
        for shp_path in shp_files:
            try:
                # Extrair nome da camada (nome da pasta pai ou do arquivo)
                layer_name = _extrair_nome_camada(shp_path)
                logger.info(f"Processando camada: {layer_name}")

                # Converter para GeoJSON
                geojson = _converter_shp_para_geojson(shp_path)

                if geojson:
                    geojson_layers[layer_name] = geojson
                    logger.info(f"Camada {layer_name} convertida com sucesso")
                else:
                    logger.warning(f"Camada {layer_name} retornou vazia")

            except Exception as e:
                logger.error(f"Erro ao processar shapefile {shp_path}: {e}")
                continue

        logger.info(f"Processamento concluído: {len(geojson_layers)} camadas extraídas")
        return geojson_layers

    except Exception as e:
        logger.error(f"Erro no processamento do shapefile: {e}")
        raise

    finally:
        # Limpar diretório temporário
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"Diretório temporário removido: {temp_dir}")
            except Exception as e:
                logger.warning(f"Erro ao remover diretório temporário: {e}")


def _extrair_nome_camada(shp_path: str) -> str:
    """
    Extrai um nome limpo para a camada baseado no caminho do shapefile
    Prioriza o nome da pasta pai sobre o nome do arquivo
    """
    path_parts = Path(shp_path).parts

    # Se houver pasta pai com nome relevante, usar ela
    if len(path_parts) >= 2:
        parent_folder = path_parts[-2]
        # Limpar nome da pasta
        clean_name = parent_folder.lower()
        clean_name = clean_name.replace(' ', '_')
        clean_name = clean_name.replace('-', '_')
        # Remover extensões comuns
        clean_name = clean_name.replace('.zip', '')

        return clean_name

    # Caso contrário, usar nome do arquivo
    filename = Path(shp_path).stem
    return filename.lower().replace(' ', '_').replace('-', '_')


def _converter_shp_para_geojson(shp_path: str) -> Optional[dict]:
    """
    Converte um Shapefile para GeoJSON usando geopandas

    Args:
        shp_path: Caminho para o arquivo .shp

    Returns:
        Dict com GeoJSON ou None se falhar
    """
    try:
        import geopandas as gpd

        # Ler shapefile
        gdf = gpd.read_file(shp_path)

        # Verificar se tem dados
        if gdf.empty:
            logger.warning(f"Shapefile vazio: {shp_path}")
            return None

        # Converter para WGS84 (EPSG:4326) se não estiver
        if gdf.crs and gdf.crs.to_epsg() != 4326:
            logger.info(f"Convertendo de {gdf.crs} para EPSG:4326")
            gdf = gdf.to_crs(epsg=4326)

        # Converter para GeoJSON (dict)
        geojson_str = gdf.to_json()
        geojson = json.loads(geojson_str)

        # Adicionar metadados
        geojson['metadata'] = {
            'total_features': len(gdf),
            'bounds': gdf.total_bounds.tolist() if hasattr(gdf, 'total_bounds') else None,
            'crs': 'EPSG:4326'
        }

        return geojson

    except ImportError:
        # Fallback para pyshp se geopandas não estiver disponível
        logger.warning("geopandas não disponível, tentando pyshp...")
        return _converter_shp_para_geojson_pyshp(shp_path)

    except Exception as e:
        logger.error(f"Erro ao converter shapefile com geopandas: {e}")
        # Tentar fallback
        try:
            return _converter_shp_para_geojson_pyshp(shp_path)
        except:
            return None


def _converter_shp_para_geojson_pyshp(shp_path: str) -> Optional[dict]:
    """
    Fallback: Converte Shapefile para GeoJSON usando pyshp (shapefile)
    Implementação mais simples sem dependências pesadas
    """
    try:
        import shapefile as shp

        # Ler shapefile
        sf = shp.Reader(shp_path)

        # Construir GeoJSON manualmente
        features = []

        for shape_record in sf.shapeRecords():
            shape = shape_record.shape
            record = shape_record.record

            # Construir propriedades do feature
            properties = {}
            for i, field in enumerate(sf.fields[1:]):  # Pular campo de deleção
                field_name = field[0]
                properties[field_name] = record[i]

            # Construir geometria
            geometry = {
                'type': _get_geometry_type(shape.shapeType),
                'coordinates': _get_coordinates(shape)
            }

            # Construir feature
            feature = {
                'type': 'Feature',
                'properties': properties,
                'geometry': geometry
            }

            features.append(feature)

        # Construir GeoJSON
        geojson = {
            'type': 'FeatureCollection',
            'features': features,
            'metadata': {
                'total_features': len(features),
                'crs': 'EPSG:4326'  # Assumir WGS84
            }
        }

        return geojson

    except Exception as e:
        logger.error(f"Erro ao converter shapefile com pyshp: {e}")
        return None


def _get_geometry_type(shape_type: int) -> str:
    """Mapeia tipo de shape do pyshp para tipo GeoJSON"""
    mapping = {
        1: 'Point',
        3: 'LineString',
        5: 'Polygon',
        8: 'MultiPoint',
        13: 'MultiLineString',
        15: 'MultiPolygon',
    }
    return mapping.get(shape_type, 'Unknown')


def _get_coordinates(shape) -> list:
    """Extrai coordenadas do shape"""
    if hasattr(shape, 'points'):
        if hasattr(shape, 'parts') and len(shape.parts) > 1:
            # MultiPolygon ou MultiLineString
            coords = []
            parts = list(shape.parts) + [len(shape.points)]
            for i in range(len(parts) - 1):
                start = parts[i]
                end = parts[i + 1]
                part_coords = shape.points[start:end]
                coords.append(part_coords)
            return coords
        else:
            # Geometria simples
            return shape.points
    return []
