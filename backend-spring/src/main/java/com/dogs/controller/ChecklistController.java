package com.dogs.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import com.dogs.DTO.ChecklistRequest;
import com.dogs.service.ChecklistService;
import com.fasterxml.jackson.core.JsonProcessingException;

@RestController
public class ChecklistController {
	
	private final ChecklistService checklistService;

	@Autowired
    public ChecklistController(ChecklistService checklistService) {
        this.checklistService = checklistService;
    }
	
	// 사용자 전체 checklist 선택 값 보내기 (Chatbot API로 JSON 전송)
	@PostMapping("/checklist")
	public ResponseEntity<String> submitChecklist(@RequestBody ChecklistRequest request) throws JsonProcessingException {
		
		// housing에 대한 유기견 정보 → Vision Model API로 전송
		String housing = request.getHousing();
		String visionResult = checklistService.sendDogsByHousing(housing);
		
		 // 전체 체크리스트 -> Chatbot API로 전송
	    String chatbotResult = checklistService.sendChecklist(request);
        
	    // 결과 합쳐서 리턴
	    return ResponseEntity.ok(", Vision_hosuing: " + visionResult + ", Chatbot: " + chatbotResult);
    }
	
}
