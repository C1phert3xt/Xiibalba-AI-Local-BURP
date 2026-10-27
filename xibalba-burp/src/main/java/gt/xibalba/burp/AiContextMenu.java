package gt.xibalba.burp;

import burp.api.montoya.http.message.HttpRequestResponse;
import burp.api.montoya.ui.contextmenu.ContextMenuEvent;
import burp.api.montoya.ui.contextmenu.ContextMenuItemsProvider;

import javax.swing.*;
import java.awt.Component;
import java.util.List;

public class AiContextMenu implements ContextMenuItemsProvider {
    private final LocalAiClient client;
    private final FindingMapper mapper;

    public AiContextMenu(LocalAiClient client, FindingMapper mapper) {
        this.client = client;
        this.mapper = mapper;
    }

    @Override
    public List<Component> provideMenuItems(ContextMenuEvent event) {
        JMenuItem item = new JMenuItem("Analizar con IA local (Xibalba)");
        item.addActionListener(e -> {
            // Soporta seleccion en Proxy (varias) o el mensaje activo en Repeater.
            List<HttpRequestResponse> targets = event.selectedRequestResponses();
            if (targets.isEmpty()) {
                event.messageEditorRequestResponse()
                     .ifPresent(ed -> client.analyzeAsync(ed.requestResponse(), mapper));
            } else {
                targets.forEach(rr -> client.analyzeAsync(rr, mapper));
            }
        });
        return List.of(item);
    }
}
