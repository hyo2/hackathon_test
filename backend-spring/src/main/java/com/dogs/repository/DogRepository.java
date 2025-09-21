package com.dogs.repository;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import com.dogs.entity.Dog;

@Repository
public interface DogRepository extends JpaRepository<Dog, Long> {
    List<Dog> findBySizeType(String size_type); // 대형
    List<Dog> findBySizeTypeNot(String size_type); // 대형 X - 중소형
}
