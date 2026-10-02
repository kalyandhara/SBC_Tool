"""Research Lab blueprint."""


from flask import Blueprint, jsonify

research_bp = Blueprint('research', __name__, url_prefix='/api/research')

@research_bp.route('/astro_lab')
def api_astro_lab():
    from research.astro_research import astro_lab
    return jsonify(astro_lab())

@research_bp.route('/walk_forward_validation')
def api_walk_forward_validation():
    from research.astro_research import walk_forward_validation
    return jsonify(walk_forward_validation())

@research_bp.route('/canonical_market_event_model')
def api_canonical_market_event_model():
    from research.astro_research import canonical_market_event_model
    return jsonify(canonical_market_event_model())

@research_bp.route('/new_moon_efficiency_study')
def api_new_moon_efficiency_study():
    from research.astro_research import new_moon_efficiency_study
    return jsonify(new_moon_efficiency_study())

@research_bp.route('/planetary_aspect_grid')
def api_planetary_aspect_grid():
    from research.astro_research import planetary_aspect_grid
    return jsonify(planetary_aspect_grid())
