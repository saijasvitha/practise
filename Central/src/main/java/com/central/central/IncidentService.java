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

    // Approve an incident
    public IncidentDocument approveIncident(String id) {
        IncidentDocument incident = getIncidentById(id);
        incident.setStatus("APPROVED");
        return incidentRepository.save(incident);
    }

    // Reject an incident
    public IncidentDocument rejectIncident(String id) {
        IncidentDocument incident = getIncidentById(id);
        incident.setStatus("REJECTED");
        return incidentRepository.save(incident);
    }
}