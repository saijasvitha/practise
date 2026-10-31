
package com.central.central;

import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.TopicExchange;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RabbitMQConfig {

    public static final String EXCHANGE = "warroom.events";
    public static final String QUEUE = "telemetry.logs";
    public static final String ROUTING_KEY = "log.generated";

    @Bean
    public TopicExchange incidentExchange() {
        return new TopicExchange(EXCHANGE, true, false);
    }

    @Bean
    public Queue incidentQueue() {
        return new Queue(QUEUE, true);
    }

    @Bean
    public Binding incidentBinding() {
        return BindingBuilder
                .bind(incidentQueue())
                .to(incidentExchange())
                .with(ROUTING_KEY);
    }
}
