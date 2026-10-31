package com.central.central;

import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class IncidentService {

    private final IncidentRepository incidentRepository;

    public IncidentService(IncidentRepository incidentRepository) {
        this.incidentRepository = incidentRepository;
    }

    // Save a new incident
    public IncidentDocument createIncident(IncidentDocument incident) {
        incident.setStatus("PENDING_APPROVAL");
        return incidentRepository.save(incident);
    }

    // Get all incidents
    public List<IncidentDocument> getAllIncidents() {
        return incidentRepository.findAll();
    }

    // Get incident by MongoDB ID
    public IncidentDocument getIncidentById(String id) {
        return incidentRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Incident not found: " + id));
    }

    // Approve an incident and trigger AI investigation
public IncidentDocument approveIncident(String id) {

    IncidentDocument incident = getIncidentById(id);

    incident.setStatus("APPROVED");

    // Save approved incident in MongoDB
    incidentRepository.save(incident);

    try {
        // Send incident details to Python AgentAssigner
        Map response = agentClient.post()
                .uri("/api/investigations")
                .body(incident)
                .retrieve()
                .body(Map.class);

        // Store AI response in MongoDB
        incident.setAiReport(response);

        System.out.println("AI investigation triggered successfully!");

    } catch (Exception e) {
        System.err.println("AgentAssigner error: " + e.getMessage());
    }

    return incidentRepository.save(incident);
}


// Reject an incident without triggering AI
public IncidentDocument rejectIncident(String id) {

    IncidentDocument incident = getIncidentById(id);

    incident.setStatus("REJECTED");

    return incidentRepository.save(incident);
}
}
