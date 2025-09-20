package com.dogs.entity;

import java.math.BigDecimal;
import java.time.LocalDate;

import com.fasterxml.jackson.annotation.JsonFormat;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.ToString;

@Entity
@Table(name = "dog")
@Data
@NoArgsConstructor
@AllArgsConstructor
@ToString
public class Dog {
	
	@Id
	@Column(name = "dog_id")
	private Long dogId; 
	
	@Column(name = "rescue_date")
	@JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd")
	private LocalDate rescueDate; // 구조일
	
	@Column(name = "register_date")
	@JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd")
	private LocalDate registerDate; // 등록일
	
	@Column(name = "notice_period")
	private String noticePeriod; // 공고 기간
	private String processor; // 등록자
	
	private String location; // 구조 장소
	
	@Column(name = "serial_no")
	private String serialNo; // 일련번호
	
	private String name; // 이름
	private String breed; // 품종
	
	private String color; // 털색
	private String age; // 나이(추정)

	private String sex; // 성별
	private String neutered; // 중성화여부
	
	private BigDecimal weight; // 무게
	private String features; // 특징
	
	private String status; // 상태 - 입양가능
	@Column(name = "processed_date")
	@JsonFormat(shape = JsonFormat.Shape.STRING, pattern = "yyyy-MM-dd")
	private LocalDate processedDate; // 처리일
	
	@Column(name = "spcial_notes")
	private String specialNotes; // 특이사항
	
	@Column(name = "size_type")
	private String sizeType; // 크기
	private String housing; // 주거환경

}
