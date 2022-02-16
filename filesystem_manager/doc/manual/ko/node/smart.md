## 5.11 S.M.A.R.T.

### 5.11.1 S.M.A.R.T. 기능 개요

디스크의 S.M.A.R.T. 상세 정보와 테스트 결과를 확인할 수 있습니다.

출력된 상세 정보, 테스트 결과를 조회하여 디스크의 전기적, 기계적 결함으로 발생되는 장애를 사전에 감지할 수 있습니다.

<div class="notices blue element normal">
<strong>S.M.A.R.T. 정보는 1시간 주기로 갱신됩니다.</strong>

<ul>
    <li>각 속성값은 "<a href="node.xhtml#5.11.3 참고"><strong>5.11.3 참고</strong></a>" 절을 확인해주세요.</li>
</ul>
</div>

<div class="notices yellow element normal">

<strong>S.M.A.R.T. 제약 사항</strong>

<ul>
    <li>구형 디스크이거나 디스크 타입/벤더사에 따라 S.M.A.R.T. 속성에 대한 의미가 상이할 수 있습니다.</li>
    <li>하드웨어 RAID 컨트롤러는 LSI 사의 제품만 지원하고 있습니다.</li>
</ul>
</div>

### 5.11.2 S.M.A.R.T. 기능 구성 요소

#### 5.11.2.1 디스크 정보

디스크 모델, 온도, 사용 시간 등의 일반적인 정보를 출력합니다.

| 구분 | 설명 |
| ---- | ---- |
| **상태**            | 디스크의 상태를 출력합니다.<ul><li>**정상**(![ICONNORMAL](./images/icon-status-normal2.png)) - 정상 상태입니다.</li><li>**경고**(![ICONWARN](./images/icon-status-warning2.png)) - S.M.A.R.T. 속성값 중 하나 이상의 결함이 의심되는 경우 입니다.</li><li>**오류**(![ICONERR](./images/icon-status-error2.png)) - 디스크의 **Healthy** 값이 **FALIED**인 경우 출력됩니다.</li></ul> |
| **블록 장치**       | 디스크와 매핑된 블록 장치의 이름입니다. |
| **일련 번호**       | 제조사에서 부여하는 디스크의 일련번호입니다. |
| **모델**            | 제조사에서 부여하는 디스크의 모델 이름입니다. |
| **온도**            | 디스크 내부 온도입니다. |
| **크기**            | 디스크의 총 크기입니다. |
| **장치 종류**       | 디스크의 종류를 나타냅니다. 대표적인 종류로는 HDD, SSD가 있습니다. |
| **Healty**          | S.M.A.R.T. 진단 결과 입니다. <ul><li>**PASSED**: 이상 없음</li><li>**FAILED**: 결함 발생</li><li>**UNKNOWN**: S.M.A.R.T. 미지원 디스크</li></ul> |
| **S.M.A.R.T. 지원** | S.M.A.R.T. 진단을 지원하는 디스크 장치인지 출력됩니다. |
| **OS 디스크**       | 운영체제가 설치된 디스크 장치인지 출력됩니다. |
| **사용 시간**       | 디스크의 총 사용 시간이 출력됩니다. |

#### 5.11.2.2 디스크 속성

디스크의 전기적, 기계적 결함 발생 여부를 진단할 수 있는 정보를 출력합니다.

| 구분      | 설명 |
|-----------|------|
| **상태**      | S.M.A.R.T. 속성의 상태를 출력합니다.<ul><li>**정상**(![ICONNORMAL](./images/icon-status-normal2.png)) - 정상 상태입니다.</li><li>**경고**(![ICONWARN](./images/icon-status-warning2.png)) - 해당 속성의 현재 값이 임계값 이하인 경우 출력됩니다.</li></ul> |
| **ID**        | S.M.A.R.T. 속성별 식별자입니다. |
| **속성 명**   | S.M.A.R.T. 속성의 이름입니다. |
| **현재 값**   | 일반화된 원시 값입니다. 제조사나 모델에 따라 100 또는 250 또는 255 분율로 출력됩니다. |
| **최저 값**   | 디스크 총 사용 시간 중에 현재 값이 임계값에 가장 근접한 값입니다. |
| **임계 값**   | 제조사에서 지정한 임계값입니다. 현재 값이 임계값에 가까울수록 결함 발생율이 높아집니다. |
| **원시 값**   | S.M.A.R.T. 속성에 따른 온도, 회수 등과 같은 측정된 원시값입니다. |
| **속성 타입** | 현재 값이 임계값 이하인 경우 속성에 따라 다음과 같이 분류할 수 있습니다.<ul><li>**Old-age**: 기계적 마모, 노후화된 디스크</li><li>**Pre-fail**: 디스크 동작 결함</li></ul> |

#### 5.11.2.3 S.M.A.R.T. 테스트 결과

최근에 수행된 S.M.A.R.T. 테스트의 정보, 결과를 출력합니다.

<div class="notices red element normal">
<strong>S.M.A.R.T. 테스트 중 LBA 오류가 발생한다면 기술 지원을 요청하시는 것을 강력히 권고합니다.</strong>
</div>

| 구분        | 설명 |
| ----------- | ---- |
| **번호**        | 테스트 수행 번호입니다. 낮을수록 최근에 수행된 테스트입니다. |
| **진행 상태**   | 테스트 진행율이 출력됩니다. |
| **LBA 오류**    | 읽기 테스트 실패가 발생된 LBA(논리 블록 주소, Logical Block Address)입니다. |
| **사용 시간**   | 테스트 수행 당시 디스크 총 사용 시간입니다. |
| **테스트 타입** | 수행된 테스트 타입을 출력합니다.<ul><li>**short offline**: 디스크의 빠른 결함 탐지를 위해 사용됩니다. 디스크 컨트롤러에 대한 전기적 테스트, 헤더, 서보 모터에 대한 기계적 테스트, 특정 영역에 대한 읽기 및 유효성 검증을 수행합니다.</li><li>**extended offline**: 디스크 생산 과정에서 최종적으로 수행하기 위해 설계된 테스트입니다. short offline 테스트와 동일하나 시간 제한이 없고 모든 영역에 대한 읽기 및 유효성 검증을 수행합니다.</li></ul> |
| **테스트 결과** | 테스트 수행 완료 여부와 오류 발생 여부를 출력합니다.|

### 5.11.3 참고

* [S.M.A.R.T. - Wikipedia](https://ko.wikipedia.org/wiki/S.M.A.R.T.)