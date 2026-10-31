package com.central.central;

import org.springframework.data.mongodb.repository.MongoRepository;

import java.util.Optional;

public interface IncidentRepository extends MongoRepository<IncidentDocument, String> {

    Optional<IncidentDocument> findByEventId(String eventId);

}