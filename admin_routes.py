#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
管理员路由

提供翻译服务配置和管理功能
"""

import os
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from dotenv import load_dotenv
from config.manager import config_manager

load_dotenv()

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/', methods=['GET'])
def admin_index():
    """管理员主页"""
    return render_template('admin/index.html')

@admin_bp.route('/services', methods=['GET'])
def services():
    """翻译服务管理页面"""
    services = config_manager.get_all_services()
    return render_template('admin/services.html', services=services)

@admin_bp.route('/api/services', methods=['GET'])
def api_get_services():
    """API: 获取所有翻译服务"""
    services = config_manager.get_all_services()
    # 隐藏 API Key 的中间部分
    for service in services:
        if service.get('api_key'):
            key = service['api_key']
            if len(key) > 8:
                service['api_key_masked'] = key[:4] + '*' * (len(key) - 8) + key[-4:]
            else:
                service['api_key_masked'] = '*' * len(key)
        else:
            service['api_key_masked'] = ''
    return jsonify({'status': 'success', 'services': services})

@admin_bp.route('/api/services', methods=['POST'])
def api_add_service():
    """API: 添加翻译服务"""
    data = request.get_json()

    name = data.get('name', '').strip()
    service_type = data.get('type', '').strip()
    url = data.get('url', '').strip()
    model = data.get('model', '').strip()
    api_key = data.get('api_key', '').strip()
    context_length = data.get('context_length', '').strip()
    max_output_length = data.get('max_output_length', '').strip()
    is_default = data.get('is_default', False)

    if not name or not service_type:
        return jsonify({'status': 'error', 'message': '服务名称和类型不能为空'}), 400

    success = config_manager.save_service(
        name=name,
        service_type=service_type,
        url=url or None,
        model=model or None,
        api_key=api_key or None,
        context_length=context_length or None,
        max_output_length=max_output_length or None,
        is_default=is_default
    )

    if success:
        # 获取刚添加的服务并检查状态
        service = config_manager.get_service(name)
        if service and api_key:  # 只有提供了API Key才检查状态
            is_healthy, status_message = config_manager.check_service_health(service)
            status = 'healthy' if is_healthy else 'unhealthy'
            config_manager.update_service_status(service['id'], status)

        return jsonify({'status': 'success', 'message': '服务添加成功'})
    else:
        return jsonify({'status': 'error', 'message': '服务添加失败'}), 500

@admin_bp.route('/api/services/<int:service_id>', methods=['PUT'])
def api_update_service(service_id):
    """API: 更新翻译服务"""
    data = request.get_json()

    name = data.get('name', '').strip()
    service_type = data.get('type', '').strip()
    url = data.get('url', '').strip()
    model = data.get('model', '').strip()
    api_key = data.get('api_key')  # Use None as sentinel - absent means don't change
    context_length = data.get('context_length', '').strip()
    max_output_length = data.get('max_output_length', '').strip()

    if not name or not service_type:
        return jsonify({'status': 'error', 'message': '服务名称和类型不能为空'}), 400

    # api_key=None means don't change (key not in request or explicit 'dont_change')
    # api_key='' means clear the key
    # api_key='xxx' means set to xxx
    if api_key is not None:
        api_key = api_key.strip() or None  # Empty string becomes None (clear)

    success = config_manager.update_service(
        service_id=service_id,
        name=name,
        service_type=service_type,
        url=url or None,
        model=model or None,
        api_key=api_key,
        context_length=context_length or None,
        max_output_length=max_output_length or None
    )

    if success:
        return jsonify({'status': 'success', 'message': '服务更新成功'})
    else:
        return jsonify({'status': 'error', 'message': '服务更新失败'}), 500

@admin_bp.route('/api/services/<int:service_id>', methods=['DELETE'])
def api_delete_service(service_id):
    """API: 删除翻译服务"""
    success = config_manager.delete_service_by_id(service_id)

    if success:
        return jsonify({'status': 'success', 'message': '服务删除成功'})
    else:
        return jsonify({'status': 'error', 'message': '服务删除失败'}), 500

@admin_bp.route('/api/services/<int:service_id>/default', methods=['POST'])
def api_set_default_service(service_id):
    """API: 设置默认翻译服务"""
    success = config_manager.set_default_service(service_id)

    if success:
        return jsonify({'status': 'success', 'message': '已设置为默认服务'})
    else:
        return jsonify({'status': 'error', 'message': '设置默认服务失败'}), 500

@admin_bp.route('/api/services/<int:service_id>/check', methods=['POST'])
def api_check_service(service_id):
    """API: 检查服务状态"""
    services = config_manager.get_all_services()
    service = next((s for s in services if s['id'] == service_id), None)

    if not service:
        return jsonify({'status': 'error', 'message': '服务不存在'}), 404

    is_healthy, status_message = config_manager.check_service_health(service)
    status = 'healthy' if is_healthy else 'unhealthy'
    config_manager.update_service_status(service_id, status)

    return jsonify({
        'status': 'success',
        'healthy': is_healthy,
        'message': status_message
    })

@admin_bp.route('/api/services/check-all', methods=['POST'])
def api_check_all_services():
    """API: 检查所有服务状态"""
    services = config_manager.get_all_services()
    results = []

    for service in services:
        if service.get('api_key') or service['type'] == 'ollama':
            is_healthy, status_message = config_manager.check_service_health(service)
            status = 'healthy' if is_healthy else 'unhealthy'
            config_manager.update_service_status(service['id'], status)
            results.append({
                'id': service['id'],
                'name': service['name'],
                'status': status,
                'message': status_message
            })

    return jsonify({
        'status': 'success',
        'results': results
    })
