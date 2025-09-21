package com.dogs.service;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import com.dogs.client.VisionClient;

@Service
public class ImgService {

	private final VisionClient visionClient;
	
	@Autowired
	public ImgService(VisionClient visionClient){
        this.visionClient = visionClient;
    }
	
	public String sendUserImg(MultipartFile image) {
		
		// Vision쪽 API로 데이터 전송
        return visionClient.sendUserImg(image).block();
	}

}
