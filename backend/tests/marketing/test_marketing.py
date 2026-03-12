# Tests módulo marketing (campaña, segmento, envío, tracking, unsubscribe)
import sys
from pathlib import Path
import json

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))


def test_segment_creation(app, db):
    from app import MarketingSegment
    with app.app_context():
        s = MarketingSegment(name='Test segment', query_rules='{"pais": "Panama"}')
        db.session.add(s)
        db.session.commit()
        assert s.id
        assert s.name == 'Test segment'
        db.session.delete(s)
        db.session.commit()


def test_template_creation(app, db):
    from app import MarketingTemplate
    with app.app_context():
        t = MarketingTemplate(
            name='Test template',
            html='<p>Hola {{nombre}}</p>',
            variables='["nombre"]'
        )
        db.session.add(t)
        db.session.commit()
        assert t.id
        db.session.delete(t)
        db.session.commit()


def test_campaign_creation(app, db):
    from app import MarketingSegment, MarketingTemplate, MarketingCampaign
    with app.app_context():
        seg = MarketingSegment(name='S', query_rules='{}')
        tpl = MarketingTemplate(name='T', html='<p>Hi</p>', variables='[]')
        db.session.add_all([seg, tpl])
        db.session.commit()
        c = MarketingCampaign(
            name='C1', subject='Test', template_id=tpl.id,
            segment_id=seg.id, status='draft'
        )
        db.session.add(c)
        db.session.commit()
        assert c.id and c.status == 'draft'
        db.session.delete(c)
        db.session.delete(tpl)
        db.session.delete(seg)
        db.session.commit()


def test_render_template():
    from _app.modules.marketing.service import render_template_html
    html = render_template_html(
        '<p>Hola {{nombre}}</p>',
        '["nombre"]',
        {'nombre': 'Juan', 'user_id': 1},
        base_url='https://example.com'
    )
    assert 'Juan' in html
    assert 'unsubscribe' in html or '1' in html


def test_unsubscribe_user(app, db):
    from app import User
    from _app.modules.marketing.service import unsubscribe_user
    with app.app_context():
        u = User.query.filter_by(email_marketing_status='subscribed').first()
        if u:
            old = u.email_marketing_status
            unsubscribe_user(u.id)
            u2 = User.query.get(u.id)
            assert u2.email_marketing_status == 'unsubscribed'
            u2.email_marketing_status = old
            db.session.commit()
