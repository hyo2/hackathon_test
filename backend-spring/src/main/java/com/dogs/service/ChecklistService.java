package com.dogs.service;

import java.util.List;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import com.dogs.DTO.ChecklistRequest;
import com.dogs.client.ChatbotClient;
import com.dogs.client.VisionClient;
import com.dogs.entity.Dog;
import com.dogs.repository.DogRepository;
import com.fasterxml.jackson.core.JsonProcessingException;

@Service
public class ChecklistService {
	
	private final VisionClient visionClient;
	private final ChatbotClient chatbotClient;
	
	private final DogRepository dogRepository;
	
	@Autowired
	public ChecklistService(ChatbotClient chatbotClient, VisionClient visionClient, DogRepository dogRepository) {
        this.visionClient = visionClient;
        this.chatbotClient = chatbotClient;
        this.dogRepository = dogRepository;
    }

    // housing 선택값에 따른 견종(대형/중소형) -> 모델로 전송
	public String sendDogsByHousing(String housing) throws JsonProcessingException {
		
		// TODO: FastAPI에 /animals/housing 엔드포인트 구현 필요
		// 현재는 임시로 더미 응답 반환
		/*
		List<Dog> housingDogs;
		
        if ("yard".equals(housing)) {
            // 마당 있는 집 -> 대형견 조회
        	housingDogs = dogRepository.findBySizeType("대형");
        } else {
            // 그 외 -> 대형견 제외(중/소형)
        	housingDogs = dogRepository.findBySizeTypeNot("대형");
        }
        
        // Vision쪽 API로 데이터 전송
        return visionClient.sendHousingDogs(housingDogs).block();
        */
        return "Housing API not implemented yet";
    }

	public String sendChecklist(ChecklistRequest request) throws JsonProcessingException {
		// checklist json 값 확인
		System.out.println(request.toString());
		// 챗봇 API로 데이터 전송
		return chatbotClient.sendChecklist(request).block(); // Mono<String> → String;
	}
}
