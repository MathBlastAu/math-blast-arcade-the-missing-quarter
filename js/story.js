/* Math Blast Arcade - story script.
 * Every spoken line lives here so text, subtitles and voice files stay in sync.
 * Voice files are assets/voice/<id>.mp3 (see tools/voice.py). Lines without a
 * voice file still show as text.
 * who: narrator | jake | priya | phantom
 * face: portrait frame name (see assets/manifest/characters.json -> portraits)
 */
window.MB = window.MB || {};
MB.STORY = {
  lines: {
    // ---- opening cinematic -------------------------------------------------
    n01: { who: 'narrator', text: 'Kepler Station. The busiest fuel stop on the Interstellar Fuel Network.' },
    n02: { who: 'narrator', text: 'Three cargo ships are waiting to launch. But tonight, the fuel gauges make no sense.' },
    n03: { who: 'narrator', text: 'Junior Fuel Inspector Jake Nova is about to dock for his very first solo mission.' },
    j01: { who: 'jake', face: 'jake_neutral', text: 'Kepler Station, this is Inspector Nova. First solo job. I will calculate this carefully.' },

    // ---- area 1: docking bay ----------------------------------------------
    p01: { who: 'priya', face: 'priya_neutral', text: 'You must be the inspector. I am Fuel Officer Priya, and we have a problem.' },
    p02: { who: 'priya', face: 'priya_neutral', text: 'Yesterday every tank on this station was full. Today, each one is missing exactly one quarter.' },
    j02: { who: 'jake', face: 'jake_worried', text: 'One quarter from every tank? That is not a leak. That is a pattern.' },
    p03: { who: 'priya', face: 'priya_neutral', text: 'The trail leads deep into the station. Collect the fuel quarters you find. Four quarters make one whole.' },
    p04: { who: 'priya', face: 'priya_neutral', text: 'And be careful. Something has scrambled the maintenance robots.' },
    j03: { who: 'jake', face: 'jake_happy', text: 'I am on it!' },
    p05: { who: 'priya', face: 'priya_neutral', text: 'The gate ahead needs one whole power cell. I can see four quarter cells on the way. Find all four.' },
    j04: { who: 'jake', face: 'jake_happy', text: 'One quarter, two quarters, three quarters, four quarters. That makes one whole!' },
    f01: { who: 'phantom', face: 'phantom_neutral', text: 'Good evening, Inspector. I am the Fraction Phantom.' },
    f02: { who: 'phantom', face: 'phantom_neutral', text: 'I took one quarter from each tank. No more, no less. I have only been fair.' },
    j05: { who: 'jake', face: 'jake_worried', text: 'Fair? Three ships cannot launch! Come back here!' },
    f03: { who: 'phantom', face: 'phantom_glitch', text: 'Follow me, Inspector. If your fractions are sharp enough.' },

    // ---- area 2: fraction bridge ------------------------------------------
    p06: { who: 'priya', face: 'priya_neutral', text: 'The energy bridge is out. It has to reach exactly one whole to cross the gap.' },
    p07: { who: 'priya', face: 'priya_neutral', text: 'Use the console. Add energy cells until the bridge is exactly the right length.' },
    j06: { who: 'jake', face: 'jake_worried', text: 'The bridge only reaches three quarters. The missing quarter again!' },
    j07: { who: 'jake', face: 'jake_happy', text: 'Three quarters plus one quarter makes one whole. Bridge restored!' },
    p08: { who: 'priya', face: 'priya_neutral', text: 'This next bridge is measured in eighths. Look for cells that are worth the same amount.' },
    j08: { who: 'jake', face: 'jake_happy', text: 'Two eighths is the same as one quarter. They are equivalent fractions!' },
    p18: { who: 'priya', face: 'priya_smile', text: 'Last bridge. This one is long, so you will need more than one cell.' },
    j14: { who: 'jake', face: 'jake_happy', text: 'Halves, quarters and eighths, all adding up to one whole.' },

    // ---- area 3: reactor core ---------------------------------------------
    p09: { who: 'priya', face: 'priya_neutral', text: 'Careful, Jake. Each reactor only runs at one exact level. Too little and it stalls. Too much and it vents.' },
    p10: { who: 'priya', face: 'priya_neutral', text: 'Jump up and bump the fuel blocks to add energy. Then pull the lever to test it.' },
    j09: { who: 'jake', face: 'jake_happy', text: 'One quarter plus two quarters is three quarters. Reactor online!' },
    f04: { who: 'phantom', face: 'phantom_neutral', text: 'Adding is easy, Inspector. But can you take away?' },
    j10: { who: 'jake', face: 'jake_happy', text: 'Seven eighths take away two eighths leaves five eighths. Exactly right!' },
    j15: { who: 'jake', face: 'jake_happy', text: 'Six eighths is the same as three quarters. Full power!' },

    // ---- area 4: zero-gravity sector --------------------------------------
    p11: { who: 'priya', face: 'priya_neutral', text: 'Gravity is switched off in this sector. Your jumps will carry you a long way.' },
    p12: { who: 'priya', face: 'priya_neutral', text: 'Those gates only open for the larger fraction. Compare before you leap.' },
    j11: { who: 'jake', face: 'jake_happy', text: 'Three eighths is less than one half. So one half is the bigger one.' },
    p13: { who: 'priya', face: 'priya_neutral', text: 'Those pods are a number line. Hop from the smallest fraction to the largest.' },
    f05: { who: 'phantom', face: 'phantom_neutral', text: 'You are closer than you think, Inspector. And further than you know.' },

    // ---- area 5: showdown -------------------------------------------------
    f06: { who: 'phantom', face: 'phantom_neutral', text: 'Welcome to the control core. From here, I shared out the fuel.' },
    j12: { who: 'jake', face: 'jake_worried', text: 'You did not share it. You took it. Where did the fuel go?' },
    f07: { who: 'phantom', face: 'phantom_glitch', text: 'Break my shield, if you can match it. Exactly. Not a fraction more.' },
    p14: { who: 'priya', face: 'priya_neutral', text: 'Jake, use the restorer cannon! Charge it to match the shield, then fire!' },
    f08: { who: 'phantom', face: 'phantom_glitch', text: 'Precise. I did not expect that.' },
    f09: { who: 'phantom', face: 'phantom_neutral', text: 'Then let us change the denominator.' },
    p15: { who: 'priya', face: 'priya_neutral', text: 'The cannon counts in eighths now! How many eighths make one half?' },
    f10: { who: 'phantom', face: 'phantom_neutral', text: 'Too much can be just as wrong as too little.' },
    p16: { who: 'priya', face: 'priya_neutral', text: 'It has overcharged the cannon! You will have to take some away!' },
    f11: { who: 'phantom', face: 'phantom_glitch', text: 'Three quarters, over three nights. One quarter each night. All of it sent to Station Vega.' },
    f12: { who: 'phantom', face: 'phantom_neutral', text: 'You have found the missing quarter, Inspector. But not the reason.' },
    j13: { who: 'jake', face: 'jake_worried', text: 'Station Vega. That is on the far side of the Fog Nebula.' },
    p17: { who: 'priya', face: 'priya_smile', text: 'You did it, Jake! The fuel is flowing again. All three ships can launch!' },
    n04: { who: 'narrator', text: 'The missing quarter was back where it belonged. But the trail of the Fraction Phantom led on, into the Fog Nebula.' },
    n05: { who: 'narrator', text: 'To be continued.' },

    // ---- short reusable feedback (Priya on the radio) -----------------------
    k01: { who: 'priya', face: 'priya_smile', text: 'Exactly right!' },
    k02: { who: 'priya', face: 'priya_smile', text: 'Perfect measurement!' },
    k03: { who: 'priya', face: 'priya_smile', text: 'Brilliant thinking, Jake!' },
    k04: { who: 'priya', face: 'priya_neutral', text: 'Not quite enough. Look at the gap that is left.' },
    k05: { who: 'priya', face: 'priya_neutral', text: 'That is too much. It went past the mark.' },
    k06: { who: 'priya', face: 'priya_smile', text: 'Good try. Every test tells you something.' }
  },
  names: { narrator: '', jake: 'JAKE', priya: 'PRIYA', phantom: 'FRACTION PHANTOM' }
};
