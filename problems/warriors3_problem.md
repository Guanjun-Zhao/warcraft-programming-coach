### **魔兽世界三(开战)**

#### **题目基本信息**

- **时间限制**: 2000ms
- **内存限制**: 65536kB

#### **题目描述**

魔兽世界的西面是红魔军的司令部，东面是蓝魔军的司令部。两个司令部之间是依次排列的若干城市，城市从西向东依次编号为1,2,3 .... N (N <= 20)。红魔军的司令部算作编号为0的城市，蓝魔军的司令部算作编号为N+1的城市。司令部有生命元，用于制造武士。

两军的司令部都会制造武士。武士一共有dragon、ninja、iceman、lion、wolf五种。每种武士都有编号、生命值、攻击力这三种属性。

双方的武士编号都是从1开始计算。红方制造出来的第n个武士，编号就是n。同样，蓝方制造出来的第n个武士，编号也是n。

武士在刚降生的时候有一个初始的生命值，生命值在战斗中会发生变化，如果生命值减少到0（生命值变为负数时应当做变为0处理），则武士死亡（消失）。

武士可以拥有武器。武器有三种，sword, bomb,和arrow，编号分别为0,1,2。

**武器特性**:
- sword的攻击力是使用者当前攻击力的20%(去尾取整)
- bomb的攻击力是使用者当前攻击力的40%(去尾取整)，但是也会导致使用者受到攻击，对使用者的攻击力是对敌人取整后的攻击力的1/2(去尾取整)。Bomb一旦使用就没了
- arrow的攻击力是使用者当前攻击力的30%(去尾取整)。一个arrow用两次就没了

**战斗规则**:
1. 在奇数编号城市，红武士先发起攻击
2. 在偶数编号城市，蓝武士先发起攻击
3. 战斗开始前，双方先对自己的武器排好使用顺序，然后再一件一件地按顺序使用。编号小的武器，排在前面。若有多支arrow，用过的排在前面
4. 双方轮流使用武器，甲用过一件，就轮到乙用。某一方把自己所有的武器都用过一轮后，就从头开始再用一轮。如果某一方没有武器了，那就挨打直到死去或敌人武器用完
5. 如果双方武器都用完且都还活着，则战斗以平局结束。如果双方都死了，也算平局
6. 有可能由于武士自身攻击力太低，而导致武器攻击力为0。攻击力为0的武器也要使用。如果战斗中双方的生命值和武器的状态都不再发生变化，则战斗结束，算平局
7. 战斗的胜方获得对方手里的武器。武士手里武器总数不超过10件。缴获武器时，按照武器种类编号从小到大缴获。如果有多件arrow，优先缴获没用过的
8. 如果战斗开始前双方都没有武器，则战斗视为平局。如果先攻击方没有武器，则由后攻击方攻击

**武士特性**:
- 编号为n的dragon降生时即获得编号为n%3的武器。dragon在战斗结束后，如果还没有战死，就会欢呼
- 编号为n的ninjia降生时即获得编号为n%3和(n+1)%3的武器。ninja使用bomb不会让自己受伤
- 编号为n的iceman降生时即获得编号为n%3的武器。iceman每前进一步，生命值减少10%(减少的量要去尾取整)
- 编号为n的lion降生时即获得编号为n%3的武器。lion有"忠诚度"这个属性，其初始值等于它降生之后其司令部剩余生命元的数目。每前进一步忠诚度就降低K。忠诚度降至0或0以下，则该lion逃离战场,永远消失。但是已经到达敌人司令部的lion不会逃跑。lion在己方司令部可能逃跑
- wolf降生时没有武器，但是在战斗开始前会抢到敌人编号最小的那种武器。如果敌人有多件这样的武器，则全部抢来。Wolf手里武器也不能超过10件。如果敌人arrow太多没法都抢来，那就先抢没用过的。如果敌人也是wolf，则不抢武器

**时间事件安排**:
- 在每个整点（每个小时的第0分）：双方的司令部中各有一个武士降生
- 在每个小时的第5分：该逃跑的lion就在这一时刻逃跑了
- 在每个小时的第10分：所有的武士朝敌人司令部方向前进一步
- 在每个小时的第35分：在有wolf及其敌人的城市，wolf要抢夺对方的武器
- 在每个小时的第40分：在有两个武士的城市，会发生战斗
- 在每个小时的第50分：司令部报告它拥有的生命元数量
- 在每个小时的第55分：每个武士报告其拥有的武器情况

**制造顺序**:
- 红方司令部按照iceman、lion、wolf、ninja、dragon的顺序制造武士
- 蓝方司令部按照lion、dragon、ninja、iceman、wolf的顺序制造武士

**其他规则**:
- 制造一个初始生命值为m的武士，司令部中的生命元就要减少m个
- 如果司令部中的生命元不足以制造某本该造的武士，那就从此停止制造武士
- 武士到达对方司令部后就算完成任务了，从此就呆在那里无所事事
- 任何一方的司令部里若是出现了敌人，则认为该司令部已被敌人占领
- 任何一方的司令部被敌人占领，则战争结束。战争结束之后就不会发生任何事情了

#### **事件类型与输出格式**

1. **武士降生**
   - 格式: `时间 blue/red 武士类型 编号 born`
   - 示例: `000:00 blue dragon 1 born`
   - 如果造出的是lion，还要多输出一行: `Its loyalty is 忠诚度`

2. **lion逃跑**
   - 格式: `时间 blue/red lion 编号 ran away`
   - 示例: `000:05 blue lion 1 ran away`

3. **武士前进到某一城市**
   - 格式: `时间 red/blue 武士类型 编号 marched to city 城市编号 with 生命值 elements and force 攻击力`
   - 示例: `000:10 red iceman 1 marched to city 1 with 20 elements and force 30`
   - 对于iceman,输出的生命值应该是变化后的数值

4. **wolf抢敌人的武器**
   - 格式: `时间 blue/red wolf 编号 took 数量 武器类型 from red/blue 武士类型 敌人编号 in city 城市编号`
   - 示例: `000:35 blue wolf 2 took 3 bomb from red dragon 2 in city 4`

5. **报告战斗情况**
   - 杀死敌人: `时间 red/blue 武士类型 编号 killed blue/red 武士类型 敌人编号 in city 城市编号 remaining 剩余生命值 elements`
   - 双方都死: `时间 both red 武士类型 编号 and blue 武士类型 敌人编号 died in city 城市编号`
   - 双方都活: `时间 both red 武士类型 编号 and blue 武士类型 敌人编号 were alive in city 城市编号`
   - 注意: 把红武士写前面

6. **武士欢呼**
   - 格式: `时间 blue/red dragon 编号 yelled in city 城市编号`
   - 示例: `003:40 blue dragon 2 yelled in city 4`

7. **武士抵达敌军司令部**
   - 格式: `时间 red/blue 武士类型 编号 reached blue/red headquarter with 生命值 elements and force 攻击力`
   - 示例: `001:10 red iceman 1 reached blue headquarter with 20 elements and force 30`

8. **司令部被占领**
   - 格式: `时间 blue/red headquarter was taken`
   - 示例: `003:10 blue headquarter was taken`

9. **司令部报告生命元数量**
   - 格式: `时间 生命值数量 elements in red/blue headquarter`
   - 示例: `000:50 100 elements in red headquarter`

10. **武士报告情况**
    - 格式: `时间 blue/red 武士类型 编号 has sword数量 sword bomb数量 bomb arrow数量 arrow and 生命值 elements`
    - 示例: `000:55 blue wolf 2 has 2 sword 3 bomb 0 arrow and 7 elements`
    - 交代武器情况时，次序依次是：sword, bomb, arrow

**输出顺序规则**:
- 首先按时间顺序输出
- 同一时间发生的事件，按发生地点从西向东依次输出
- 武士前进的事件,算是发生在目的地
- 在一次战斗中有可能发生5至6号事件。这些事件都算同时发生，其时间就是战斗开始时间。一次战斗中的这些事件，序号小的应该先输出
- 两个武士同时抵达同一城市，则先输出红武士的前进事件，后输出蓝武士的
- 对于同一城市，同一时间发生的事情，先输出红方的，后输出蓝方的
- 8号事件发生之前的一瞬间一定发生了7号事件。输出时，这两件事算同一时间发生，但是应先输出7号事件
- 虽然任何一方的司令部被占领之后，就不会有任何事情发生了。但和司令部被占领同时发生的事件，全都要输出

#### **输入格式**

第一行是t,代表测试数据组数

每组样例共三行：
1. 第一行：4个整数 M,N,K,T
   - M: 每个司令部一开始都有M个生命元 (1 <= M <= 100000)
   - N: 两个司令部之间一共有N个城市 (1 <= N <= 20)
   - K: lion每前进一步，忠诚度就降低K (0 <= K <= 100)
   - T: 要求输出从0时0分开始，到时间T为止(包括T)的所有事件。T以分钟为单位，0 <= T <= 6000
2. 第二行：五个整数，依次是dragon、ninja、iceman、lion、wolf的初始生命值。它们都大于0小于等于200
3. 第三行：五个整数，依次是dragon、ninja、iceman、lion、wolf的攻击力。它们都大于0小于等于200

#### **输出格式**

对每组数据，先输出一行：`Case n:` (如对第一组数据就输出 `Case 1:`)

然后按恰当的顺序和格式输出到时间T为止发生的所有事件。每个事件都以事件发生的时间开头，时间格式是"时:分"，"时"有三位，"分"有两位。

#### **样例输入**

```plaintext
1
20 1 10 400
20 20 30 10 20
5 5 5 5 5
```

#### **样例输出**

```plaintext
Case 1:
000:00 blue lion 1 born
Its loyalty is 10
000:10 blue lion 1 marched to city 1 with 10 elements and force 5
000:50 20 elements in red headquarter
000:50 10 elements in blue headquarter
000:55 blue lion 1 has 0 sword 1 bomb 0 arrow and 10 elements
001:05 blue lion 1 ran away
001:50 20 elements in red headquarter
001:50 10 elements in blue headquarter
002:50 20 elements in red headquarter
002:50 10 elements in blue headquarter
003:50 20 elements in red headquarter
003:50 10 elements in blue headquarter
004:50 20 elements in red headquarter
004:50 10 elements in blue headquarter
005:50 20 elements in red headquarter
005:50 10 elements in blue headquarter
```

#### **提示**

请注意浮点数精度误差问题。OJ上的编译器编译出来的可执行程序，在这方面和你电脑上执行的程序很可能会不一致。5 * 0.3 的结果，有的机器上可能是 15.00000001，去尾取整得到15,有的机器上可能是14.9999999，去尾取整后就变成14。因此,本题不要写 5 * 0.3，要写 5 * 3 / 10。