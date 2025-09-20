package com.dogs.controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import com.dogs.service.ImgService;

@RestController
public class ImgController {

    private final ImgService imgService;
    
    @Autowired
    public ImgController(ImgService imgService) {
        this.imgService = imgService;
    }

    @PostMapping(value = "/classify", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<String> submitImg(@RequestParam("image") MultipartFile image) {
    	
    	System.out.println("받은 파일 이름: " + image.getOriginalFilename());
        System.out.println("받은 파일 크기: " + image.getSize() + " bytes");
        System.out.println("받은 파일 타입: " + image.getContentType());
        
        String visionResult = imgService.sendUserImg(image);
        
    	return ResponseEntity.ok("Vision_userImg: " + visionResult);
    }
}