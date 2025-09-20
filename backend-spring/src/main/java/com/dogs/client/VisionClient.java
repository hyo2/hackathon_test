package com.dogs.client;

import java.util.List;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;

import com.dogs.entity.Dog;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;

import reactor.core.publisher.Mono;

@Component
public class VisionClient {

	private final WebClient webClient;

	public VisionClient(@Value("${ai.base-url}") String baseUrl, WebClient.Builder builder) {
		this.webClient = builder.baseUrl(baseUrl).build();
	}

	// 크기에 따른 유기견 정보 전송
	public Mono<String> sendHousingDogs(List<Dog> dogs) throws JsonProcessingException {

		ObjectMapper mapper = new ObjectMapper();
		mapper.registerModule(new JavaTimeModule());
		String json = mapper.writeValueAsString(dogs);
		System.out.println("Vision API로 전송하는 housingDogs JSON: " + json);

		try {
		return webClient.post().uri("/housing") // Vision Model API - 크기에 따른 유기견 정보 전송 엔드포인트
				.contentType(MediaType.APPLICATION_JSON).bodyValue(dogs) // List<Dog> → JSON 자동 변환
				.retrieve().bodyToMono(String.class);
		} catch (WebClientResponseException e) {
		    System.out.println("Vision API - housingDogs 호출 실패: " + e.getStatusCode() + ", " + e.getResponseBodyAsString());
		    return Mono.just("Vision API - housingDogs 호출 실패");
		}
	}

	// 이미지 변환
	private byte[] toBytes(MultipartFile file) {
		try {
			return file.getBytes();
		} catch (Exception e) {
			throw new RuntimeException("이미지 변환 실패", e);
		}
	}

	// formData 값 map에 담기
	private MultiValueMap<String, Object> buildMultipartBody(MultipartFile file) {
		LinkedMultiValueMap<String, Object> map = new LinkedMultiValueMap<>();
		map.add("image", new ByteArrayResource(toBytes(file)) {
			@Override
			public String getFilename() {
				return file.getOriginalFilename();
			}
		});
		return map;
	}

	// 사용자 이미지 전송
	public Mono<String> sendUserImg(MultipartFile image) {
		
		try {
		return webClient.post().uri("/ai/classify") // 원래 프론트에 있던 임시 경로(필요시 수정)
				.contentType(MediaType.MULTIPART_FORM_DATA)
				.bodyValue(buildMultipartBody(image))
				.retrieve()
				.bodyToMono(String.class);
		} catch (WebClientResponseException e) {
		    System.out.println("Vision API - userImg 호출 실패: " + e.getStatusCode() + ", " + e.getResponseBodyAsString());
		    return Mono.just("Vision API -userImg 호출 실패");
		}
	}

}
