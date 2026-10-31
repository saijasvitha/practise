package com.central.central;

import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/incidents")
public class IncidentController {

    private final IncidentService incidentService;

    public IncidentController(IncidentService incidentService) {
        this.incidentService = incidentService;
    }

    // Get all incidents
    @GetMapping
    public List<IncidentDocument> getAllIncidents() {
        return incidentService.getAllIncidents();
    }

    // Get one incident by ID
    @GetMapping("/{id}")
    public IncidentDocument getIncidentById(@PathVariable String id) {
        return incidentService.getIncidentById(id);
    }

    // Approve an incident
    @PostMapping("/{id}/approve")
    public IncidentDocument approveIncident(@PathVariable String id) {
        return incidentService.approveIncident(id);
    }

    // Reject an incident
    @PostMapping("/{id}/reject")
    public IncidentDocument rejectIncident(@PathVariable String id) {
        return incidentService.rejectIncident(id);
    }
}