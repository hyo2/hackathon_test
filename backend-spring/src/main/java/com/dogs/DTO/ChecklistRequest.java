package com.dogs.DTO;

import com.fasterxml.jackson.annotation.JsonProperty;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.ToString;

@Data
@NoArgsConstructor
@AllArgsConstructor
@ToString
public class ChecklistRequest {
	private String gender; // 보호자 성별
    private String housing; // 보호자 주거 환경
    private String family; // 보호자 가족 구성
    
    @JsonProperty("time_with_pet")
    private String timeWithPet; // 보호자가 함께 있을 수 있는 시간
    
    @JsonProperty("walking_freq")
    private String walkingFreq; // 산책 가능 횟수
}
