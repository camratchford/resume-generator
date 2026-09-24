import pytest

from resume_generator.md import create_markdown_renderer


@pytest.fixture
def render():
    renderer = create_markdown_renderer()

    def render_markdown(text):
        renderer.reset()
        return renderer.convert(text).replace("\n", "")

    return render_markdown


def test_columns(render):
    html = render("%% left || right %%")

    assert '<div class="row"><div class="column">left</div><div class="column">right</div></div>' in html


def test_flex_wrap_renders_one_bubble_per_item(render):
    html = render("%( Python || Bash )%")

    assert '<div class="flex-wrap"><div class="bubble">Python</div><div class="bubble">Bash</div></div>' in html


def test_flex_wrap_skips_empty_items(render):
    html = render("%( Python |||| Bash || )%")

    assert html.count('class="bubble"') == 2


def test_muted_text(render):
    assert '<span class="muted-text">Diploma</span>' in render("%m Diploma m%")


def test_nerdfont_glyph(render):
    assert '<span class="nf">\U000f01f0</span>' in render("%+\U000f01f0+%")


def test_nerdfont_glyph_requires_a_single_character(render):
    assert 'class="nf"' not in render("%+ab+%")


def test_page_break(render):
    assert '<div class="page"></div>' in render("%:pg:%")


def test_plain_markdown_still_renders(render):
    html = render("# Heading\n\n- item")

    assert "<h1>Heading</h1>" in html
    assert "<li>item</li>" in html


def test_extra_extension_modules_are_loaded():
    renderer = create_markdown_renderer("resume_generator.md.extensions")

    assert '<div class="page"></div>' in renderer.convert("%:pg:%")
