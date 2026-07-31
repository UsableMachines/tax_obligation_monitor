/* ─── Tax Obligation Monitor — JavaScript ─── */
document.addEventListener('DOMContentLoaded', function () {

  /* ── Sidebar Toggle ── */
  const sidebar = document.getElementById('sidebar');
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebarToggleMobile = document.getElementById('sidebarToggleMobile');

  if (sidebarToggle) {
    sidebarToggle.addEventListener('click', function () {
      sidebar.classList.toggle('collapsed');
    });
  }

  if (sidebarToggleMobile) {
    sidebarToggleMobile.addEventListener('click', function () {
      sidebar.classList.toggle('mobile-open');
    });

    /* Close sidebar when clicking outside on mobile */
    document.addEventListener('click', function (e) {
      if (sidebar.classList.contains('mobile-open') &&
          !sidebar.contains(e.target) &&
          e.target !== sidebarToggleMobile) {
        sidebar.classList.remove('mobile-open');
      }
    });
  }

  /* ── Theme Toggle ── */
  const themeToggle = document.getElementById('themeToggle');
  const themeIcon = document.getElementById('themeIcon');

  function updateThemeIcon() {
    const theme = document.documentElement.getAttribute('data-theme');
    if (themeIcon) {
      themeIcon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
  }

  if (themeToggle) {
    updateThemeIcon();
    themeToggle.addEventListener('click', function () {
      const current = document.documentElement.getAttribute('data-theme') || 'light';
      const next = current === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', next);
      updateThemeIcon();

      /* Persist via settings endpoint */
      const csrfToken = document.querySelector('input[name="csrf_token"]');
      const formData = new FormData();
      formData.append('theme', next);
      if (csrfToken) formData.append('csrf_token', csrfToken.value);

      fetch(window.location.origin + '/settings', {
        method: 'POST',
        body: formData,
        credentials: 'same-origin',
      }).catch(function () { /* Best-effort */ });
    });
  }

  /* ── Help Panel ── */
  const helpToggle = document.getElementById('helpToggle');
  const helpPanel = document.getElementById('helpPanel');
  const helpClose = document.getElementById('helpClose');

  if (helpToggle && helpPanel) {
    helpToggle.addEventListener('click', function () {
      helpPanel.classList.toggle('open');
    });
  }

  if (helpClose && helpPanel) {
    helpClose.addEventListener('click', function () {
      helpPanel.classList.remove('open');
    });
  }

  /* ── AI Analysis ── */
  document.querySelectorAll('.analyze-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const entityType = this.getAttribute('data-entity-type');
      const entityId = this.getAttribute('data-entity-id');
      runAnalysis(entityType, entityId);
    });
  });
});


function runAnalysis(entityType, entityId) {
  const modal = document.getElementById('analysisModal');
  const resultDiv = document.getElementById('analysisResult');

  if (!modal || !resultDiv) return;

  modal.style.display = 'flex';
  resultDiv.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i> Analyzing with AI agent...</div>';

  const csrfMeta = document.querySelector('input[name="csrf_token"]');
  const headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };
  if (csrfMeta) {
    headers['X-CSRFToken'] = csrfMeta.value;
  }

  fetch(window.location.origin + '/api/analyze', {
    method: 'POST',
    headers: headers,
    credentials: 'same-origin',
    body: JSON.stringify({
      entity_type: entityType,
      entity_id: parseInt(entityId),
      operation: 'analyze',
    }),
  })
    .then(function (resp) { return resp.json(); })
    .then(function (data) {
      resultDiv.innerHTML = renderAnalysisResult(data);
    })
    .catch(function (err) {
      resultDiv.innerHTML = '<div class="alert alert-danger">Analysis failed: ' + err.message + '</div>';
    });
}


function renderAnalysisResult(data) {
  if (data.status === 'error') {
    return '<div class="alert alert-danger">' + (data.summary || 'Analysis failed.') + '</div>';
  }

  var html = '<div class="analysis-result">';

  /* Summary */
  if (data.summary) {
    html += '<div class="analysis-summary"><p>' + escapeHtml(data.summary) + '</p></div>';
  }

  /* Score */
  html += '<div class="analysis-score">';
  html += '<div class="score-value">' + (data.score != null ? data.score.toFixed(1) : '—') + '</div>';
  html += '<div>';
  html += '<div><strong>Risk Level:</strong> <span class="risk-badge risk-' + (data.risk_level || 'medium') + '">' + (data.risk_level || 'N/A') + '</span></div>';
  if (data.confidence != null) {
    html += '<div style="margin-top:4px"><strong>Confidence:</strong> ' + (data.confidence * 100).toFixed(0) + '%</div>';
  }
  html += '</div></div>';

  /* Findings */
  if (data.findings && data.findings.length > 0) {
    html += '<div class="analysis-section"><h4>Findings</h4>';
    data.findings.forEach(function (f) {
      html += '<div class="finding-item">';
      html += '<strong><span class="risk-badge risk-' + (f.severity || 'medium') + '">' + (f.severity || '') + '</span> ' + escapeHtml(f.category || '') + '</strong>';
      html += '<p>' + escapeHtml(f.description || '') + '</p>';
      if (f.recommendation) {
        html += '<p><em>Recommendation: ' + escapeHtml(f.recommendation) + '</em></p>';
      }
      html += '</div>';
    });
    html += '</div>';
  }

  /* Recommendations */
  if (data.recommendations && data.recommendations.length > 0) {
    html += '<div class="analysis-section"><h4>Recommendations</h4>';
    data.recommendations.forEach(function (r) {
      html += '<div class="rec-item">';
      html += '<strong>' + escapeHtml(r.priority || '') + ': ' + escapeHtml(r.action || '') + '</strong>';
      if (r.rationale) {
        html += '<p>' + escapeHtml(r.rationale) + '</p>';
      }
      if (r.owner_role) {
        html += '<p><small>Owner: ' + escapeHtml(r.owner_role) + '</small></p>';
      }
      html += '</div>';
    });
    html += '</div>';
  }

  html += '</div>';
  return html;
}


function closeAnalysisModal() {
  var modal = document.getElementById('analysisModal');
  if (modal) modal.style.display = 'none';
}


function escapeHtml(text) {
  var div = document.createElement('div');
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}
