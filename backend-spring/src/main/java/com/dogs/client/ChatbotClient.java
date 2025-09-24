package com.dogs.client;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;

import com.dogs.DTO.ChecklistRequest;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

import reactor.core.publisher.Mono;

@Component
public class ChatbotClient {

	private final WebClient webClient;

	public ChatbotClient(@Value("${chatbot.base-url}") String baseUrl, WebClient.Builder builder) {
		this.webClient = builder.baseUrl(baseUrl).build();
	}

	// 챗봇에 체크리스트 값 보내기
	public Mono<String> sendChecklist(ChecklistRequest request) throws JsonProcessingException {

		ObjectMapper mapper = new ObjectMapper();
		String json = mapper.writeValueAsString(request);
		System.out.println("Chatbot API로 전송하는 JSON: " + json);

		try {
			return webClient.post().uri("/checklist").contentType(MediaType.APPLICATION_JSON).bodyValue(request)
					.retrieve().bodyToMono(String.class);
		} catch (WebClientResponseException e) {
			System.out.println("Chatbot API 호출 실패: " + e.getStatusCode() + ", " + e.getResponseBodyAsString());
			return Mono.just("Chatbot API 호출 실패: " + e.getMessage());
		}
	}

}
