"""
Photos Views Module

This module provides the photos views for the web interface.
"""

import os
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_from_directory
from werkzeug.utils import secure_filename
from datetime import datetime

from src.utils.config import get_config
from src.utils.logging import get_logger
from src.utils.paths import get_path_manager
from src.utils.registry import get_registry

# Get logger
logger = get_logger('web.photos')

# Create blueprint
bp = Blueprint('photos', __name__, url_prefix='/photos')

def allowed_file(filename):
    """Check if a file has an allowed extension."""
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/')
@bp.route('/<tab>')
def index(tab=None):
    """Render the photos page with pagination."""
    # Get path manager
    path_manager = get_path_manager()

    # Добавляем логирование
    logger.info(f"Запрос на отображение страницы с фотографиями, tab={tab}")

    # Determine active tab
    active_tab = tab or request.args.get('tab', 'downloads')
    if active_tab not in ['downloads', 'analyzed', 'upload_ready', 'uploaded']:
        active_tab = 'downloads'

    # Get page and items per page from query parameters
    # Если вкладка указана в URL, то всегда показываем первую страницу
    if tab:
        page = 1
    else:
        page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)  # Default 12 items per page

    logger.info(f"Активная вкладка: {active_tab}, страница: {page}, элементов на странице: {per_page}")

    # Get photos from different directories
    downloads = []
    logger.info(f"Сканирование директории downloads: {path_manager.downloads_dir}")
    try:
        files = os.listdir(path_manager.downloads_dir)
        # Фильтруем только файлы с разрешенными расширениями
        image_files = [f for f in files if allowed_file(f)]
        logger.info(f"Найдено файлов в downloads: {len(files)}, из них изображений: {len(image_files)}")
        for filename in image_files:
            file_path = os.path.join(path_manager.downloads_dir, filename)
            logger.info(f"Добавление файла: {filename}")
            downloads.append({
                'name': filename,
                'path': file_path,
                'size': os.path.getsize(file_path),
                'modified': datetime.fromtimestamp(os.path.getmtime(file_path))
            })
    except Exception as e:
        logger.error(f"Ошибка при сканировании директории downloads: {str(e)}")

    analyzed = []
    logger.info(f"Сканирование директории analysis: {path_manager.analysis_dir}")
    try:
        files = os.listdir(path_manager.analysis_dir)
        # Фильтруем только файлы с расширением .json
        json_files = [f for f in files if f.endswith('.json')]
        logger.info(f"Найдено файлов в analysis: {len(files)}, из них JSON: {len(json_files)}")
        for filename in json_files:
            file_path = os.path.join(path_manager.analysis_dir, filename)
            photo_name = filename.replace('_analysis.json', '')
            logger.info(f"Добавление файла анализа: {filename}")

            # Try to find the original photo
            original_path = None
            original_filename = None

            # Сначала ищем в директории processed
            processed_path = os.path.join(path_manager.processed_dir, photo_name)
            if os.path.exists(processed_path):
                original_path = processed_path
                original_filename = photo_name
            else:
                # Пробуем с разными расширениями
                for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
                    test_path = os.path.join(path_manager.processed_dir, photo_name + ext)
                    if os.path.exists(test_path):
                        original_path = test_path
                        original_filename = photo_name + ext
                        break

            # Если не нашли в processed, ищем в downloads
            if not original_path:
                downloads_path = os.path.join(path_manager.downloads_dir, photo_name)
                if os.path.exists(downloads_path):
                    original_path = downloads_path
                    original_filename = photo_name
                else:
                    # Пробуем с разными расширениями
                    for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
                        test_path = os.path.join(path_manager.downloads_dir, photo_name + ext)
                        if os.path.exists(test_path):
                            original_path = test_path
                            original_filename = photo_name + ext
                            break

            # Если не нашли в downloads, ищем в uploaded
            if not original_path:
                uploaded_path = os.path.join(path_manager.uploaded_dir, photo_name)
                if os.path.exists(uploaded_path):
                    original_path = uploaded_path
                    original_filename = photo_name
                else:
                    # Пробуем с разными расширениями
                    for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
                        test_path = os.path.join(path_manager.uploaded_dir, photo_name + ext)
                        if os.path.exists(test_path):
                            original_path = test_path
                            original_filename = photo_name + ext
                            break

            analyzed.append({
                'name': photo_name,
                'analysis_path': file_path,
                'original_path': original_path,
                'original_filename': original_filename,
                'size': os.path.getsize(file_path),
                'modified': datetime.fromtimestamp(os.path.getmtime(file_path))
            })
    except Exception as e:
        logger.error(f"Ошибка при сканировании директории analysis: {str(e)}")

    upload_ready = []
    logger.info(f"Сканирование директории upload: {path_manager.upload_dir}")
    try:
        files = os.listdir(path_manager.upload_dir)
        # Фильтруем только файлы с разрешенными расширениями
        image_files = [f for f in files if allowed_file(f)]
        logger.info(f"Найдено файлов в upload: {len(files)}, из них изображений: {len(image_files)}")
        for filename in image_files:
            file_path = os.path.join(path_manager.upload_dir, filename)
            logger.info(f"Добавление файла для загрузки: {filename}")

            # Check if metadata exists
            metadata_path = os.path.join(path_manager.upload_metadata_dir, os.path.splitext(filename)[0] + '.json')
            metadata = None
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading metadata for {filename}: {str(e)}")

            upload_ready.append({
                'name': filename,
                'path': file_path,
                'metadata_path': metadata_path if os.path.exists(metadata_path) else None,
                'metadata': metadata,
                'size': os.path.getsize(file_path),
                'modified': datetime.fromtimestamp(os.path.getmtime(file_path))
            })
    except Exception as e:
        logger.error(f"Ошибка при сканировании директории upload: {str(e)}")

    uploaded = []
    logger.info(f"Сканирование директории uploaded: {path_manager.uploaded_dir}")
    try:
        files = os.listdir(path_manager.uploaded_dir)
        # Фильтруем только файлы с разрешенными расширениями
        image_files = [f for f in files if allowed_file(f)]
        logger.info(f"Найдено файлов в uploaded: {len(files)}, из них изображений: {len(image_files)}")
        for filename in image_files:
            file_path = os.path.join(path_manager.uploaded_dir, filename)
            logger.info(f"Добавление файла: {filename}")

            # Check if metadata exists
            metadata_path = os.path.join(path_manager.uploaded_dir, os.path.splitext(filename)[0] + '.json')
            metadata = None
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading metadata for {filename}: {str(e)}")

            uploaded.append({
                'name': filename,
                'path': file_path,
                'metadata_path': metadata_path if os.path.exists(metadata_path) else None,
                'metadata': metadata,
                'size': os.path.getsize(file_path),
                'modified': datetime.fromtimestamp(os.path.getmtime(file_path))
            })
    except Exception as e:
        logger.error(f"Ошибка при сканировании директории uploaded: {str(e)}")

    # Sort all lists by modified date (newest first)
    downloads = sorted(downloads, key=lambda x: x['modified'], reverse=True)
    analyzed = sorted(analyzed, key=lambda x: x['modified'], reverse=True)
    upload_ready = sorted(upload_ready, key=lambda x: x['modified'], reverse=True)
    uploaded = sorted(uploaded, key=lambda x: x['modified'], reverse=True)

    # Create pagination for the active tab
    if active_tab == 'downloads':
        items = downloads
    elif active_tab == 'analyzed':
        items = analyzed
    elif active_tab == 'upload_ready':
        items = upload_ready
    else:  # uploaded
        items = uploaded

    # Calculate pagination
    total_items = len(items)
    total_pages = (total_items + per_page - 1) // per_page  # Ceiling division

    # Ensure page is within valid range
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages

    # Get items for current page
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_items)
    current_items = items[start_idx:end_idx] if items else []

    # Create pagination info
    pagination = {
        'page': page,
        'per_page': per_page,
        'total_items': total_items,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_page': page - 1 if page > 1 else None,
        'next_page': page + 1 if page < total_pages else None,
        'pages': range(max(1, page - 2), min(total_pages + 1, page + 3))
    }

    return render_template('photos/index.html',
                          downloads=downloads,
                          analyzed=analyzed,
                          upload_ready=upload_ready,
                          uploaded=uploaded,
                          active_tab=active_tab,
                          current_items=current_items,
                          pagination=pagination)

@bp.route('/upload', methods=['POST'])
def upload():
    """Upload photos."""
    if 'photos' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('photos.index'))

    files = request.files.getlist('photos')

    if not files or files[0].filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('photos.index'))

    path_manager = get_path_manager()
    uploaded_count = 0

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(path_manager.downloads_dir, filename)

            # Save the file
            file.save(file_path)
            uploaded_count += 1
            logger.info(f"Uploaded file: {filename}")

    if uploaded_count > 0:
        flash(f'Successfully uploaded {uploaded_count} photos', 'success')
    else:
        flash('No valid photos uploaded', 'warning')

    return redirect(url_for('photos.index'))

@bp.route('/view/<path:filename>')
def view_photo(filename):
    """View a photo."""
    path_manager = get_path_manager()

    # Логируем запрос для отладки
    logger.info(f"Запрос на просмотр фото: {filename}")
    logger.info(f"Пути поиска: downloads_dir={path_manager.downloads_dir}, analysis_dir={path_manager.analysis_dir}, upload_dir={path_manager.upload_dir}, uploaded_dir={path_manager.uploaded_dir}")

    # Проверяем существование директорий
    for dir_name, dir_path in {
        'downloads_dir': path_manager.downloads_dir,
        'analysis_dir': path_manager.analysis_dir,
        'upload_dir': path_manager.upload_dir,
        'uploaded_dir': path_manager.uploaded_dir,
        'processed_dir': path_manager.processed_dir
    }.items():
        if not os.path.exists(dir_path):
            logger.warning(f"Директория {dir_name} не существует: {dir_path}")
        else:
            logger.info(f"Директория {dir_name} существует: {dir_path}")
            # Выводим список файлов в директории (только первые 5 для краткости)
            files = os.listdir(dir_path)[:5]
            logger.info(f"Файлы в {dir_name} (первые 5): {files}")

    # Determine which directory the file is in
    if os.path.exists(os.path.join(path_manager.downloads_dir, filename)):
        logger.info(f"Фото найдено в downloads_dir: {filename}")
        return send_from_directory(path_manager.downloads_dir, filename)
    elif os.path.exists(os.path.join(path_manager.analysis_dir, filename)):
        logger.info(f"Фото найдено в analysis_dir: {filename}")
        return send_from_directory(path_manager.analysis_dir, filename)
    elif os.path.exists(os.path.join(path_manager.upload_dir, filename)):
        logger.info(f"Фото найдено в upload_dir: {filename}")
        return send_from_directory(path_manager.upload_dir, filename)
    elif os.path.exists(os.path.join(path_manager.uploaded_dir, filename)):
        logger.info(f"Фото найдено в uploaded_dir: {filename}")
        return send_from_directory(path_manager.uploaded_dir, filename)
    elif os.path.exists(os.path.join(path_manager.processed_dir, filename)):
        logger.info(f"Фото найдено в processed_dir: {filename}")
        return send_from_directory(path_manager.processed_dir, filename)
    else:
        logger.warning(f"Фото не найдено: {filename}")
        flash(f"File not found: {filename}", "danger")
        return redirect(url_for('photos.index'))

@bp.route('/analysis/<path:filename>')
def view_analysis(filename):
    """View analysis for a photo."""
    path_manager = get_path_manager()
    logger.info(f"Запрос на просмотр анализа для файла: {filename}")

    # Сначала проверяем, есть ли файл анализа в директории analysis
    analysis_path = os.path.join(path_manager.analysis_dir, filename)
    if not analysis_path.endswith('.json'):
        analysis_path += '_analysis.json'

    analysis = None
    original_path = None
    photo_name = filename.replace('_analysis.json', '')

    # Если файл анализа существует в директории analysis
    if os.path.exists(analysis_path):
        try:
            with open(analysis_path, 'r', encoding='utf-8') as f:
                analysis = json.load(f)
            logger.info(f"Загружен файл анализа из директории analysis: {analysis_path}")
        except Exception as e:
            logger.error(f"Ошибка при загрузке файла анализа из директории analysis: {str(e)}")

    # Если файл анализа не найден в директории analysis, проверяем в директории uploaded
    if not analysis:
        # Проверяем, есть ли JSON-файл с тем же именем в директории uploaded
        uploaded_json_path = os.path.join(path_manager.uploaded_dir, os.path.splitext(filename)[0] + '.json')
        if os.path.exists(uploaded_json_path):
            try:
                with open(uploaded_json_path, 'r', encoding='utf-8') as f:
                    analysis = json.load(f)
                logger.info(f"Загружен файл метаданных из директории uploaded: {uploaded_json_path}")
            except Exception as e:
                logger.error(f"Ошибка при загрузке файла метаданных из директории uploaded: {str(e)}")

    # Если анализ найден, ищем оригинальное фото
    if analysis:
        # Ищем оригинальное фото в разных директориях
        for dir_path in [path_manager.processed_dir, path_manager.downloads_dir, path_manager.uploaded_dir]:
            for ext in ['', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
                photo_path = os.path.join(dir_path, photo_name + ext)
                if os.path.exists(photo_path):
                    original_path = url_for('photos.view_photo', filename=photo_name + ext)
                    logger.info(f"Найдено оригинальное фото: {photo_path}")
                    break
            if original_path:
                break

        return render_template('photos/analysis.html',
                              filename=filename,
                              analysis=analysis,
                              original_path=original_path)
    else:
        flash(f"Analysis not found for: {filename}", "danger")
        return redirect(url_for('photos.index'))
