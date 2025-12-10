# Markdown提示词系统快速实施指南

**基于**: MARKDOWN_TRANSLATION_ANALYSIS_AND_OPTIMIZATION.md 第9.1节  
**目标**: 让Markdown翻译与ePub翻译共享提示词系统  
**预计时间**: 3-5天

---

## 实施步骤

### Step 1: 前端添加提示词选择UI (1天)

**文件**: `templates/markdown_translate.html`

#### 1.1 在文件上传区域下方添加提示词选择框

```html
<!-- 位置: 在文件信息显示区域之后，翻译按钮之前 -->
<div id="prompt-section" class="mt-4 p-4 bg-gray-50 rounded-lg">
    <label for="prompt-template" class="block text-sm font-medium text-gray-700 mb-2">
        提示词模板:
    </label>
    <select id="prompt-template" class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
        <option value="">加载中...</option>
    </select>
    
    <div id="custom-prompt-container" class="mt-3 hidden">
        <label for="custom-prompt" class="block text-sm font-medium text-gray-700 mb-2">
            自定义提示词:
        </label>
        <textarea id="custom-prompt" class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500" 
                  rows="4" placeholder="输入自定义翻译提示词..."></textarea>
        <p class="text-xs text-gray-500 mt-1">提示: 自定义提示词将覆盖选择的模板</p>
    </div>
</div>
```

#### 1.2 在JavaScript中添加提示词加载逻辑

```javascript
// 位置: $(document).ready() 内部，服务加载之后

// 加载提示词模板
$.get('/prompt-templates', function(templates) {
    const select = $('#prompt-template');
    select.empty();
    select.append('<option value="">请选择提示词模板</option>');
    
    Object.keys(templates).forEach(key => {
        select.append(`<option value="${key}">${templates[key].name}</option>`);
    });
    
    console.log('提示词模板加载完成');
}).fail(function() {
    console.error('加载提示词模板失败');
    $('#prompt-template').html('<option value="">加载失败</option>');
});

// 模板切换事件
$('#prompt-template').change(function() {
    const selected = $(this).val();
    if (selected) {
        $('#custom-prompt-container').removeClass('hidden');
    } else {
        $('#custom-prompt-container').addClass('hidden');
        $('#custom-prompt').val('');  // 清空自定义提示词
    }
});
```

#### 1.3 在翻译请求中添加提示词参数

```javascript
// 位置: $('#translate-btn').click() 内部，data对象中

$('#translate-btn').click(function() {
    var data = {
        filename: $('#filename').text(),
        target_language: $('#target-language').val(),
        service_name: $('#service-select').val(),
        ollama_url: $('#ollama-url').val(),
        ollama_model: $('#ollama-model').val(),
        
        // 添加提示词参数
        prompt_template: $('#prompt-template').val(),
        custom_prompt: $('#custom-prompt').val()
    };
    
    // ... 其他代码 ...
});
```

### Step 2: 后端添加提示词参数支持 (1天)

**文件**: `app.py`

#### 2.1 修改translate_markdown路由

```python
# 位置: 第763-794行
@app.route('/translate-markdown', methods=['POST'])
def translate_markdown():
    """专门处理Markdown文件翻译的路由"""
    app.logger.debug("Accessing translate-markdown route")
    data = request.json
    app.logger.debug(f"Received data: {data}")
    filename = data['filename']
    target_language = data['target_language']

    # Service selection - support both old ollama params and new service selection
    service_name = data.get('service_name')
    ollama_url = data.get('ollama_url', 'http://localhost:11434/api/generate')
    ollama_model = data.get('ollama_model', 'qwen2.5:7b')

    # 添加提示词参数接收
    custom_prompt = data.get('custom_prompt')
    prompt_template = data.get('prompt_template')

    if service_name:
        # Use configured service
        translation_service = TranslationService(service_name_from_config=service_name)
    else:
        # Fallback to default service
        default_service = get_default_service()
        translation_service = TranslationService(service_name_from_config=default_service)

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if not os.path.exists(file_path):
        app.logger.error(f"File not found: {file_path}")
        abort(404, description="File not found")

    # 启动Markdown翻译任务，传递提示词参数
    threading.Thread(
        target=translate_markdown_task, 
        args=(file_path, target_language, translation_service, custom_prompt)
    ).start()

    return jsonify({'status': 'started'})
```

#### 2.2 修改translate_markdown_task函数

```python
# 位置: 第513-564行
def translate_markdown_task(file_path, target_language, translation_service, custom_prompt=None):
    """Markdown翻译任务 - 专门处理Markdown文件"""
    # 重置进度状态
    reset_progress_state()
    progress_state['status'] = 'in_progress'

    try:
        progress_queue.put(('progress', '开始处理Markdown文件...'))

        # 预测试API服务连接
        progress_queue.put(('progress', '正在测试翻译服务连接...'))
        success, message = translation_service.test_connection()
        if not success:
            error_msg = f"翻译服务连接测试失败: {message}"
            app.logger.error(error_msg)
            progress_queue.put(('error', error_msg))
            progress_state['status'] = 'error'
            progress_state['error_message'] = error_msg
            return

        progress_queue.put(('progress', f'服务连接测试成功: {message}'))

        # 直接使用增强的Markdown翻译函数，传递custom_prompt
        translated_content = translate_markdown_with_enhanced_preservation(
            file_path, translation_service, target_language, progress_queue, custom_prompt
        )

        # 生成输出文件名
        output_filename = f"{os.path.splitext(os.path.basename(file_path))[0]}_translated_{target_language}"
        base_output_path = os.path.join(app.config['RESULT_FOLDER'], output_filename + '.txt')

        # 保存翻译后的Markdown
        md_path = base_output_path.replace('.txt', '.md')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(translated_content)

        # 同时生成HTML预览
        html_path = base_output_path.replace('.txt', '.html')
        markdown_parser = ImprovedMarkdownParser()
        generator = EnhancedFormatPreservingGenerator(markdown_parser)
        generator.generate_html_from_content(translated_content, html_path)

        # 返回结果
        progress_queue.put(('complete', os.path.basename(md_path)))
        progress_state['status'] = 'complete'
        progress_state['result_file'] = os.path.basename(md_path)

    except Exception as e:
        app.logger.error(f"Markdown翻译任务失败: {e}")
        progress_queue.put(('error', f'Markdown翻译失败: {str(e)}'))
        progress_state['status'] = 'error'
        progress_state['error_message'] = str(e)
```

#### 2.3 修改translate_markdown_with_enhanced_preservation函数

```python
# 位置: 第904-1000行
def translate_markdown_with_enhanced_preservation(
    file_path, translation_service, target_language, progress_queue, custom_prompt=None
):
    """
    增强的Markdown翻译函数，集成智能内容分类和格式保留
    """
    try:
        app.logger.info("开始增强的Markdown翻译")

        # 读取Markdown内容
        with open(file_path, 'r', encoding='utf-8') as f:
            markdown_content = f.read()

        # 使用分类器分析内容
        classifier = MarkdownContentClassifier()
        classification = classifier.classify_content(markdown_content)

        progress_queue.put(('progress', f'内容分类完成: 可翻译 {len(classification["translatable_sections"])} 个段落'))

        # 创建翻译计划
        translation_plan = classifier.create_translation_plan(classification)
        app.logger.info(f"翻译计划: {translation_plan}")

        # 使用改进的解析器
        markdown_parser = ImprovedMarkdownParser()
        document_ast = markdown_parser.parse_with_ast(markdown_content)
        translatable_nodes = document_ast['translatable_nodes']

        # 过滤需要翻译的节点
        nodes_to_translate = []
        for node in translatable_nodes:
            # 检查是否需要翻译
            if node.get('should_translate', True):
                nodes_to_translate.append(node)

        progress_queue.put(('progress', f'准备翻译 {len(nodes_to_translate)} 个节点'))

        # 翻译节点，传递custom_prompt
        translated_nodes = []
        for i, node in enumerate(nodes_to_translate):
            try:
                progress_queue.put(('progress', f'翻译节点 {i+1}/{len(nodes_to_translate)}'))

                # 使用改进的翻译提示，传递custom_prompt
                translated_text = translation_service.translate_chunk(
                    node['text'],
                    target_language=target_language,
                    source_language='auto',
                    custom_prompt=custom_prompt  # 新增参数
                )

                translated_node = {
                    'text': translated_text,
                    'type': node['type'],
                    'formatting': node.get('formatting', []),
                    'original_node': node.get('original_node'),
                    'context': node.get('context', {})
                }
                translated_nodes.append(translated_node)

            except Exception as e:
                app.logger.error(f"翻译节点失败: {e}")
                # 失败时保留原节点
                translated_nodes.append(node)

        # 重建Markdown
        generator = EnhancedFormatPreservingGenerator(markdown_parser)
        rebuilt_content = markdown_parser.rebuild_with_translations(translated_nodes)

        progress_queue.put(('progress', 'Markdown重建完成'))

        # 验证翻译质量
        progress_queue.put(('progress', '验证翻译质量...'))
        try:
            from markdown_translation_validator import MarkdownTranslationValidator
            validator = MarkdownTranslationValidator()
            validation_result = validator.validate_translation(markdown_content, rebuilt_content)

            # 记录验证结果
            app.logger.info(f"翻译验证结果: 总体分数 {validation_result['overall_score']:.1f}/10")

            if validation_result['overall_score'] >= 6:
                progress_queue.put(('progress', f'✅ 翻译质量验证通过: {validation_result["overall_score"]:.1f}/10'))
            else:
                progress_queue.put(('progress', f'⚠️ 翻译质量有待改进: {validation_result["overall_score"]:.1f}/10'))

                # 记录问题
                for issue in validation_result.get('issues', []):
                    app.logger.warning(f"翻译问题: {issue}")

        except Exception as e:
            app.logger.warning(f"翻译验证失败: {e}")
            progress_queue.put(('progress', '⚠️ 翻译验证跳过'))

        return rebuilt_content

    except Exception as e:
        app.logger.error(f"增强Markdown翻译失败: {e}")
        progress_queue.put(('progress', f'翻译失败: {str(e)}'))
        raise
```

### Step 3: 测试验证 (1天)

#### 3.1 功能测试清单

- [ ] 前端正确加载6种提示词模板
- [ ] 选择模板后显示自定义提示词编辑框
- [ ] 自定义提示词可以正常输入和保存
- [ ] 翻译请求中包含prompt_template和custom_prompt参数
- [ ] 后端正确接收custom_prompt参数
- [ ] 自定义提示词正确传递到翻译调用
- [ ] 翻译结果符合自定义提示词要求

#### 3.2 测试用例

```javascript
// 测试1: 选择预设模板
$('#prompt-template').val('technical').change();
// 应该显示自定义提示词编辑框

// 测试2: 输入自定义提示词
$('#custom-prompt').val('这是自定义提示词');
// 应该能正常输入

// 测试3: 发送翻译请求
$('#translate-btn').click();
// 检查网络请求中的data是否包含prompt_template和custom_prompt
```

### Step 4: 样式调整 (半天)

为了保持与ePub翻译页面一致，建议添加CSS样式：

```css
/* 在markdown_translate.html的<style>标签中添加 */
#prompt-section {
    transition: all 0.3s ease;
}

#prompt-template option {
    padding: 8px;
}

#custom-prompt {
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    resize: vertical;
}
```

## 验收标准

### 功能验收
1. ✅ 用户可以在Markdown翻译页面选择6种预设提示词模板
2. ✅ 用户可以输入自定义提示词，覆盖预设模板
3. ✅ 翻译结果符合选择的提示词要求
4. ✅ 与ePub翻译的提示词系统体验完全一致

### 代码验收
1. ✅ 前端代码符合现有代码规范
2. ✅ 后端参数传递链路完整
3. ✅ 错误处理完善
4. ✅ 日志记录完整

## 潜在问题与解决方案

### 问题1: 提示词模板加载失败
**现象**: 前端显示"加载中..."后一直是空白  
**解决**: 检查网络请求，确认 `/prompt-templates` API正常返回

### 问题2: 自定义提示词不生效
**现象**: 输入自定义提示词后翻译结果没有变化  
**解决**: 检查后端是否正确接收和传递custom_prompt参数

### 问题3: 与现有翻译逻辑冲突
**现象**: 添加提示词后翻译功能异常  
**解决**: 确认custom_prompt参数为可选参数，不影响现有逻辑

## 后续优化建议

1. **智能提示词选择**: 根据内容类型自动推荐提示词模板
2. **提示词模板管理**: 在管理界面允许编辑和添加自定义模板
3. **提示词历史**: 记录用户常用的提示词模板
4. **提示词验证**: 检查自定义提示词的格式和有效性

---

**实施完成后，Markdown翻译系统将与ePub翻译系统共享完整的提示词管理功能！**
