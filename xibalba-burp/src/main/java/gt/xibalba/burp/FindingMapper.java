package gt.xibalba.burp;

import burp.api.montoya.MontoyaApi;
import burp.api.montoya.http.message.HttpRequestResponse;
import burp.api.montoya.scanner.audit.issues.AuditIssue;
import burp.api.montoya.scanner.audit.issues.AuditIssueConfidence;
import burp.api.montoya.scanner.audit.issues.AuditIssueSeverity;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

public class FindingMapper {
    private final MontoyaApi api;

    public FindingMapper(MontoyaApi api) { this.api = api; }

    public void registerFindings(String aiJson, HttpRequestResponse rr) {
        JsonArray findings;
        try {
            findings = JsonParser.parseString(aiJson).getAsJsonArray();
        } catch (Exception e) {
            api.logging().logToError("[Xibalba] La IA no devolvio JSON valido: " + e.getMessage());
            return;
        }

        String baseUrl = rr.request() != null ? rr.request().url() : "http://local/";

        for (var el : findings) {
            JsonObject f = el.getAsJsonObject();
            AuditIssueSeverity sev = severity(text(f, "severity", "INFO"));

            // Firma Montoya (orden exacto, 10 parametros; el ultimo es varargs):
            // name, detail, remediation, baseUrl, severity, confidence,
            // background, remediationBackground, typicalSeverity, requestResponses...
            AuditIssue issue = AuditIssue.auditIssue(
                "[IA] " + text(f, "title", "Hallazgo sin titulo"),
                "<p>" + esc(text(f, "detail", "")) + "</p>"
                    + "<p><b>Evidencia:</b> " + esc(text(f, "evidence", "")) + "</p>",
                "<p>" + esc(text(f, "remediation", "Revision manual requerida.")) + "</p>",
                baseUrl,
                sev,
                confidence(text(f, "confidence", "TENTATIVE")),
                "Hallazgo generado por analisis con modelo local (Xibalba). Verificar manualmente.",
                "Revisar el hallazgo contra el flujo real antes de reportarlo al cliente.",
                sev,
                rr   // request/response como evidencia adjunta (varargs)
            );
            // Aparece en Dashboard -> Issues / Target -> Site map.
            api.siteMap().add(issue);
            api.logging().logToOutput("[Xibalba] Hallazgo registrado: " + text(f, "title", ""));
        }
    }

    private String text(JsonObject o, String k, String def) {
        return o.has(k) && !o.get(k).isJsonNull() ? o.get(k).getAsString() : def;
    }

    // Escapa HTML: el contenido viene del modelo sobre datos del objetivo (no confiable).
    private String esc(String s) {
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
    }

    private AuditIssueSeverity severity(String s) {
        return switch (s.toUpperCase()) {
            case "HIGH"   -> AuditIssueSeverity.HIGH;
            case "MEDIUM" -> AuditIssueSeverity.MEDIUM;
            case "LOW"    -> AuditIssueSeverity.LOW;
            default       -> AuditIssueSeverity.INFORMATION;
        };
    }

    private AuditIssueConfidence confidence(String c) {
        return switch (c.toUpperCase()) {
            case "CERTAIN" -> AuditIssueConfidence.CERTAIN;
            case "FIRM"    -> AuditIssueConfidence.FIRM;
            default        -> AuditIssueConfidence.TENTATIVE;
        };
    }
}
