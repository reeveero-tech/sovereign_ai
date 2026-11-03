# -*- coding: utf-8 -*-
"""R-840: موصلات مبدئية — GitHub وGitLab وRender وSupabase والموصل العام."""
from . import (generic_openapi, github_connector, gitlab_connector,
                render_connector, supabase_connector)

__all__ = ["github_connector", "gitlab_connector", "render_connector",
           "supabase_connector", "generic_openapi"]
