"""Facebook Marketplace integration (added in v2.3).

Meta does not offer a public Marketplace listing API for individual
sellers. This package supports two workflows, both "assist" tools rather
than auto-posting:

1. Copy-paste block: a formatted title/description/price string + a
   downloadable ZIP of the item's images, which the user pastes into
   FB's web form.
2. Commerce Manager catalog CSV: a bulk export matching Meta's feed
   spec for approved business sellers.

See ``schemas.py`` for the persisted shape (stored under
``item.custom_fields.facebook``) and ``formatter.py`` for the render
helpers.
"""
