from jinja2 import Template

def jinja2_prompt_render(prompt, params):
    """
    提示词 jinja2 渲染
    """
    template = Template(prompt)
    return template.render(params)