
package com.central.central;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

@Component
public class IncidentEventListener {

    private final IncidentService incidentService;
    private final ObjectMapper objectMapper;

    public IncidentEventListener(
            IncidentService incidentService,
            ObjectMapper objectMapper) {
        this.incidentService = incidentService;
        this.objectMapper = objectMapper;
    }

    @RabbitListener(queues = RabbitMQConfig.QUEUE)
    public void receiveIncident(String message) {

        try {
            // Convert incoming JSON into a JSON tree
            JsonNode root = objectMapper.readTree(message);

            // Extract the payload
            JsonNode payload = root.path("payload");

            // Create an IncidentDocument
            IncidentDocument incident = new IncidentDocument();

            incident.setEventId(root.path("eventId").asText());
            incident.setServiceName(root.path("service").asText());
            incident.setSeverity(root.path("severity").asText());
            incident.setTitle(root.path("scenario").asText());
            incident.setDescription(
                    payload.path("message").asText()
            );
            incident.setTimestamp(root.path("timestamp").asText());

            // Store payload as metrics
            Map<String, Object> metrics =
                    objectMapper.convertValue(payload, Map.class);

            incident.setMetrics(metrics);

            // Preserve the complete original event in logs
            Map<String, Object> originalEvent =
                    objectMapper.convertValue(root, Map.class);

            incident.setLogs(List.of(originalEvent));

            // Save to MongoDB
            incidentService.createIncident(incident);

            System.out.println(
                    "Incident received and saved: "
                    + incident.getEventId()
            );

        } catch (Exception e) {
            System.err.println(
                    "Failed to process incident: " + e.getMessage()
            );

            throw new RuntimeException(
                    "Incident processing failed", e
            );
        }
    }
}
