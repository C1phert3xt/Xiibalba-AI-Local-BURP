package gt.xibalba.burp;

import burp.api.montoya.BurpExtension;
import burp.api.montoya.MontoyaApi;

public class XibalbaAiExtension implements BurpExtension {
    @Override
    public void initialize(MontoyaApi api) {
        api.extension().setName("Xibalba AI Analyzer");

        // La clave se lee del entorno (nunca hardcodeada ni en el project file).
        String apiKey = System.getenv("XIBALBA_AI_KEY");
        if (apiKey == null || apiKey.isBlank()) {
            api.logging().logToError("[Xibalba] Falta la variable de entorno XIBALBA_AI_KEY. Extension inactiva.");
            return;
        }

        LocalAiClient client = new LocalAiClient(api, apiKey);
        FindingMapper mapper = new FindingMapper(api);

        // Menu contextual: el analista decide QUE enviar (control OPSEC frente a
        // mandar todo el trafico de forma automatica a un modelo).
        api.userInterface().registerContextMenuItemsProvider(new AiContextMenu(client, mapper));
        api.logging().logToOutput("[Xibalba] AI Analyzer cargado.");
    }
}
