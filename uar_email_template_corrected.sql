-- UAR Alert Email Template (Corrected)
-- Usage: sqlite3 instance/renewalguard.db < uar_email_template_corrected.sql

INSERT INTO email_template (name, subject, body_html, category, is_active, is_system, created_at, updated_at) VALUES (
    'UAR Alert - Findings Detected',
    'User Access Review Alert: {{ findings_count }} findings detected',
    '<html><head><style>body{font-family:Arial,sans-serif;line-height:1.6;color:#333}.header{background-color:#007bff;color:white;padding:20px;text-align:center}.content{padding:20px}.summary{background-color:#f8f9fa;padding:15px;border-left:4px solid #007bff;margin:20px 0}.warning{background-color:#fff3cd;border-left:4px solid #ffc107;padding:10px;margin:15px 0}.critical{background-color:#f8d7da;border-left:4px solid #dc3545;padding:10px;margin:15px 0}.btn{background-color:#007bff;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;display:inline-block;margin:10px 0}.footer{background-color:#f8f9fa;padding:10px;text-align:center;font-size:12px;color:#666;margin-top:30px}ul{list-style-type:none;padding:0}ul li{padding:5px 0}ul li strong{display:inline-block;width:150px}</style></head><body><div class="header"><h1>User Access Review Alert</h1></div><div class="content"><p>The automated access review <strong>{{ comparison_name }}</strong> has detected <strong>{{ findings_count }}</strong> findings that require your attention.</p><div class="summary"><h3>Summary</h3><ul><li><strong>Left Only (A):</strong> {{ left_only_count }} users</li><li><strong>Right Only (B):</strong> {{ right_only_count }} users</li><li><strong>Mismatches:</strong> {{ mismatch_count }} users</li></ul></div>{% if right_only_count > 0 %}<div class="critical"><strong>Critical Alert:</strong> {{ right_only_count }} unauthorized users detected in the target system.</div>{% endif %}<p><strong>Execution Date:</strong> {{ execution_date }}</p><p style="text-align:center;margin-top:30px"><a href="{{ execution_url }}" class="btn">View Findings</a></p></div><div class="footer"><p>This is an automated alert from RenewalGuard User Access Review system.</p></div></body></html>',
    'security',
    1,
    1,
    datetime('now'),
    datetime('now')
);
